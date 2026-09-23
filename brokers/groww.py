"""Groww (India). Groww charges for its trading API, and the keys come from the
Groww Cloud API keys page, where the key has to be approved each day before it
will hand out a session. Give the desk the API key and the secret and it works
out the checksum Groww asks for (sha256 of the secret and the epoch second) and
gets the day's token itself; an account whose key is the TOTP kind gives the
authenticator secret instead. A token pasted straight from that page also works
on its own, and dies at 6 AM. Reads /v1/holdings/user and /v1/margins/detail/user.
Groww's holdings carry no price and no exchange, so the desk marks every line
from Yahoo and reads them as NSE names. Source: groww.in/trade-api/docs.

Nothing in this file places a trade."""

import hashlib
import time

import requests

from brokers import BrokerError, derive, num, totp_now

META = {
    "label": "Groww",
    "where": "India",
    "region": "in",
    "daily_login": False,
    "docs": "https://groww.in/trade-api/docs",
    "how": "The Groww Cloud API keys page (the trading API is a paid subscription): create a key, then paste the key and its secret. Groww asks you to approve the key on that page each day before it will hand out a session.",
    "fields": [
        {"env": "GROWW_API_KEY", "label": "API key", "secret": True,
         "hint": "a token pasted from the same page also works here on its own"},
        {"env": "GROWW_API_SECRET", "label": "API secret", "secret": True, "required": False},
        {"env": "GROWW_TOTP_SECRET", "label": "Authenticator secret", "secret": True, "required": False,
         "hint": "only for a key of the TOTP kind"},
    ],
}

BASE = "https://api.groww.in/v1"


def _headers(bearer):
    return {"Accept": "application/json", "X-API-VERSION": "1.0",
            "Authorization": "Bearer " + bearer}


def _session_token(cfg):
    """The day's token, from the key and whichever second thing the reader has."""
    key = cfg["GROWW_API_KEY"]
    secret = (cfg.get("GROWW_API_SECRET") or "").strip()
    totp_secret = (cfg.get("GROWW_TOTP_SECRET") or "").strip()
    if not secret and not totp_secret:
        return key                      # the reader pasted a token, not a key
    if secret:
        stamp = str(int(time.time()))
        body = {"key_type": "approval",
                "checksum": hashlib.sha256((secret + stamp).encode("utf-8")).hexdigest(),
                "timestamp": stamp}
    else:
        body = {"key_type": "totp", "totp": totp_now(totp_secret, "Groww")}
    try:
        r = requests.post(BASE + "/token/api/access",
                          headers={**_headers(key), "Content-Type": "application/json"},
                          json=body, timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Groww: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    tok = j.get("token") or (j.get("payload") or {}).get("token")
    if r.status_code != 200 or not tok:
        raise BrokerError("Groww did not hand out a session: " + str(j.get("message") or r.status_code)[:160]
                          + " Keys have to be approved on the Groww keys page each day, and the trading API is a paid subscription.")
    return tok


def _get(client, path):
    try:
        r = requests.get(BASE + path, headers=client["headers"], timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Groww: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code in (401, 403):
        raise BrokerError("Groww did not accept this session. Approve the key on the Groww keys page, and check the subscription is live.")
    if r.status_code != 200:
        raise BrokerError("Groww answered: " + str(j.get("message") or r.status_code)[:160])
    return j.get("payload") if isinstance(j.get("payload"), (dict, list)) else j


def connect(cfg, token=None):
    return {"headers": _headers(_session_token(cfg))}


def label(client):
    # Groww's read endpoints name no account, so there is no number to show.
    return "account"


def equity(client):
    d = _get(client, "/holdings/user")
    holdings = d.get("holdings") if isinstance(d, dict) else d
    rows = []
    for h in holdings if isinstance(holdings, list) else []:
        sym = h.get("trading_symbol") or ""
        rows.append(derive({
            "code": sym, "name": "", "exch": "NSE",
            "qty": num(h.get("quantity")), "avg": num(h.get("average_price")),
            "ltp": None, "value": None, "pnl": None, "pnl_pct": None, "day_pct": None,
            "currency": "INR", "ysym": sym + ".NS",
        }))
    return rows


def funds(client):
    d = _get(client, "/margins/detail/user")
    d = d if isinstance(d, dict) else {}
    return {"cash": num(d.get("clear_cash")), "currency": "INR",
            "buying_power": num(d.get("clear_cash"))}
