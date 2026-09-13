"""Zerodha, through Kite Connect (India). An app key and secret from
developers.kite.trade (Zerodha charges for a Kite Connect app), and a login
every trading day: the reader logs in on Zerodha's page, the redirect carries a
request_token, and the desk exchanges it for the day's access token
(sha256 of key + request_token + secret). The token dies at 6 AM the next day.
Reads /user/profile, /portfolio/holdings and /user/margins. Source:
kite.trade/docs/connect/v3."""

import hashlib

import requests

from brokers import BrokerError, derive, num

META = {
    "label": "Zerodha (Kite Connect)",
    "where": "India",
    "region": "in",
    "daily_login": True,
    "docs": "https://kite.trade/docs/connect/v3/",
    "how": "developers.kite.trade: create a Kite Connect app (Zerodha charges for it), set its redirect address to this desk's Settings address, and copy the API key and secret. Then log in once each trading day from this screen.",
    "fields": [
        {"env": "KITE_API_KEY", "label": "API key", "secret": True},
        {"env": "KITE_API_SECRET", "label": "API secret", "secret": True},
    ],
    "token_hint": "After the login the page jumps to your redirect address with request_token= in it; paste that value, or the whole address.",
    "token_param": "request_token",
}

BASE = "https://api.kite.trade"


def login_url(cfg):
    return f"https://kite.zerodha.com/connect/login?v=3&api_key={cfg['KITE_API_KEY']}"


def exchange_token(cfg, request_token):
    checksum = hashlib.sha256((cfg["KITE_API_KEY"] + request_token + cfg["KITE_API_SECRET"]).encode()).hexdigest()
    try:
        r = requests.post(BASE + "/session/token", headers={"X-Kite-Version": "3"},
                          data={"api_key": cfg["KITE_API_KEY"], "request_token": request_token, "checksum": checksum},
                          timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Zerodha: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code != 200 or j.get("status") != "success":
        raise BrokerError("Zerodha did not accept that login: " + str(j.get("message") or r.status_code)[:160])
    return j["data"]["access_token"]


def _get(client, path):
    r = requests.get(BASE + path, headers=client["headers"], timeout=20)
    j = r.json() if r.content else {}
    if r.status_code in (401, 403) or j.get("error_type") == "TokenException":
        raise BrokerError("Zerodha's session for today is not valid. Log in again from this screen.")
    if r.status_code != 200 or j.get("status") != "success":
        raise BrokerError("Zerodha answered: " + str(j.get("message") or r.status_code)[:160])
    return j.get("data")


def connect(cfg, token=None):
    if not token:
        return None
    client = {"headers": {"X-Kite-Version": "3", "Authorization": f"token {cfg['KITE_API_KEY']}:{token}"}}
    client["profile"] = _get(client, "/user/profile") or {}
    return client


def label(client):
    uid = str((client.get("profile") or {}).get("user_id") or "")
    return f"A/C ··{uid[-4:]}" if len(uid) >= 4 else "account"


def equity(client):
    rows = []
    for h in _get(client, "/portfolio/holdings") or []:
        qty = (num(h.get("quantity")) or 0) + (num(h.get("t1_quantity")) or 0)
        exch = h.get("exchange") or "NSE"
        sym = h.get("tradingsymbol") or ""
        rows.append(derive({
            "code": sym, "name": "", "exch": exch, "qty": qty,
            "avg": num(h.get("average_price")), "ltp": num(h.get("last_price")),
            "value": None, "pnl": num(h.get("pnl")), "pnl_pct": None,
            "day_pct": num(h.get("day_change_percentage")),
            "currency": "INR", "ysym": sym + (".BO" if exch == "BSE" else ".NS"),
        }))
    return rows


def funds(client):
    m = _get(client, "/user/margins") or {}
    eq = m.get("equity") or {}
    avail = eq.get("available") or {}
    return {"cash": num(avail.get("cash")), "currency": "INR",
            "buying_power": num(avail.get("live_balance")), "equity": num(eq.get("net"))}
