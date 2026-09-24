"""Angel One, through SmartAPI (India). Free for its clients. SmartAPI has no
redirect login: the desk signs in with the client code, the PIN and a code from
the authenticator app that Angel One makes you enrol, and gets a JWT that lasts
until midnight. The reader saves the authenticator's own secret once and the
desk works the six digits out itself, so there is nothing to paste each day.
Reads getProfile, getAllHolding (getHolding on an account SmartAPI has not
moved over yet) and getRMS. Holdings come priced. Source:
smartapi.angelone.in/docs, and the routes in Angel One's own Python library.

The PIN and the authenticator secret sit in .env on this computer, the same
place as every other broker key here. Nothing in this file places a trade."""

import socket
import uuid

import requests

from brokers import BrokerError, derive, instruments, num, pace, quote_result, quote_row, quotes_off, totp_now

META = {
    "label": "Angel One (SmartAPI)",
    "where": "India",
    "region": "in",
    "daily_login": False,
    "docs": "https://smartapi.angelone.in/docs",
    "how": "smartapi.angelone.in: create an app (free), copy its API key. Then your Angel One client code, your trading PIN, and the secret behind the authenticator QR code you scanned when you turned TOTP on. With those four the desk signs in by itself.",
    "fields": [
        {"env": "ANGEL_API_KEY", "label": "API key", "secret": True},
        {"env": "ANGEL_CLIENT_CODE", "label": "Client code", "hint": "your Angel One login id"},
        {"env": "ANGEL_PIN", "label": "Trading PIN", "secret": True},
        {"env": "ANGEL_TOTP_SECRET", "label": "Authenticator secret", "secret": True,
         "hint": "the letters shown beside the QR code when you set up TOTP, not the six digits"},
    ],
}

BASE = "https://apiconnect.angelone.in"


def _local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 53))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _headers(cfg, jwt=None):
    mac = ":".join(f"{(uuid.getnode() >> i) & 0xFF:02X}" for i in range(40, -1, -8))
    h = {"Content-type": "application/json", "Accept": "application/json",
         "X-UserType": "USER", "X-SourceID": "WEB",
         "X-ClientLocalIP": _local_ip(), "X-ClientPublicIP": _local_ip(),
         "X-MACAddress": mac, "X-PrivateKey": cfg["ANGEL_API_KEY"]}
    if jwt:
        h["Authorization"] = "Bearer " + jwt
    return h


def _call(method, path, headers, payload=None):
    try:
        r = requests.request(method, BASE + path, headers=headers, json=payload, timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Angel One: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code in (401, 403):
        raise BrokerError("Angel One did not accept this session. Check the API key, the client code and the PIN; the session also ends at midnight and the desk signs in again on its own.")
    if r.status_code != 200 or j.get("status") is False:
        raise BrokerError("Angel One answered: " + str(j.get("message") or j.get("errorcode") or r.status_code)[:160])
    return j.get("data")


def connect(cfg, token=None):
    body = {"clientcode": cfg["ANGEL_CLIENT_CODE"], "password": cfg["ANGEL_PIN"],
            "totp": totp_now(cfg["ANGEL_TOTP_SECRET"], "Angel One")}
    data = _call("POST", "/rest/auth/angelbroking/user/v1/loginByPassword",
                 _headers(cfg), body) or {}
    jwt = data.get("jwtToken") or ""
    if not jwt:
        raise BrokerError("Angel One signed in but handed back no session key. Check that TOTP is switched on for this account.")
    return {"headers": _headers(cfg, jwt.replace("Bearer ", "")), "client_code": cfg["ANGEL_CLIENT_CODE"]}


def label(client):
    code = str(client.get("client_code") or "")
    return f"A/C ··{code[-4:]}" if len(code) >= 4 else "account"


def _holdings(client):
    try:
        d = _call("GET", "/rest/secure/angelbroking/portfolio/v1/getAllHolding", client["headers"])
    except BrokerError:
        d = None
    if isinstance(d, dict) and d.get("holdings") is not None:
        return d.get("holdings") or []
    if isinstance(d, list):
        return d
    d = _call("GET", "/rest/secure/angelbroking/portfolio/v1/getHolding", client["headers"])
    return d if isinstance(d, list) else []


def equity(client):
    rows = []
    for h in _holdings(client):
        exch = (h.get("exchange") or "NSE").upper()
        sym = h.get("tradingsymbol") or ""
        # SmartAPI writes the cash series as SBIN-EQ; Yahoo knows it as SBIN.NS.
        base = sym[:-3] if sym.upper().endswith("-EQ") else sym
        rows.append(derive({
            "code": sym, "name": "", "exch": exch,
            "qty": num(h.get("quantity")), "avg": num(h.get("averageprice")),
            "ltp": num(h.get("ltp")), "value": None,
            "pnl": num(h.get("profitandloss")), "pnl_pct": num(h.get("pnlpercentage")),
            "day_pct": None,
            "currency": "INR", "ysym": base + (".BO" if exch.startswith("BSE") else ".NS"),
        }))
    return rows


def funds(client):
    d = _call("GET", "/rest/secure/angelbroking/user/v1/getRMS", client["headers"]) or {}
    return {"cash": num(d.get("availablecash")), "currency": "INR",
            "buying_power": num(d.get("availablelimitmargin")) or num(d.get("availablecash")),
            "equity": num(d.get("net"))}


def quote(client, code, exch="NSE"):
    """A live price with the order book, from POST /market/v1/quote in FULL mode, which
    SmartAPI serves free. Angel One names a stock by the exchange's number for it (2885 for
    RELIANCE on NSE), which the shared instrument list supplies. close is the previous
    session's close (the documented example: ltp 568.2, close 567.4, netChange 0.8)."""
    if quotes_off(client):
        return None
    exch = (exch or "NSE").upper()
    inst = instruments.lookup(code, exch)
    if not inst or not inst["token"]:
        return None
    pace("angel-quote", 1.05)
    try:
        r = requests.post(BASE + "/rest/secure/angelbroking/market/v1/quote/", headers=client["headers"],
                          json={"mode": "FULL", "exchangeTokens": {exch: [inst["token"]]}}, timeout=10)
        j = r.json() if r.content else {}
    except (requests.RequestException, ValueError):
        return None
    if r.status_code in (401, 403):
        return None
    if r.status_code != 200 or j.get("status") is False:
        return quote_result(client, None)
    rows = ((j.get("data") or {}).get("fetched")) or []
    q = rows[0] if rows else {}
    return quote_result(client, quote_row(code, exch, q.get("ltp"), q.get("close"),
                                          q.get("open"), q.get("high"), q.get("low"),
                                          q.get("depth"), q.get("tradeVolume")))
