"""Upstox (India). An API key and secret from the Upstox developer console
(free for its clients), and a login every trading day: the reader logs in on
Upstox's page, the redirect carries a code, and the desk exchanges it for the
day's access token. Upstox issues no refresh token and every token dies at
3:30 AM the next morning, so the login is a daily one. Reads /v2/user/profile,
/v2/portfolio/long-term-holdings and /v2/user/get-funds-and-margin. Holdings
come priced, so the desk does not mark them from Yahoo. Source:
upstox.com/developer/api-documentation."""

import os

import requests

from brokers import BrokerError, derive, num

META = {
    "label": "Upstox",
    "where": "India",
    "region": "in",
    "daily_login": True,
    "docs": "https://upstox.com/developer/api-documentation/",
    "how": "The Upstox developer console: create an app, set its redirect address to this desk's Settings address, and copy the API key and secret. Then log in once each trading day from this screen.",
    "fields": [
        {"env": "UPSTOX_API_KEY", "label": "API key", "secret": True},
        {"env": "UPSTOX_API_SECRET", "label": "API secret", "secret": True},
        {"env": "UPSTOX_REDIRECT_URI", "label": "Redirect address", "required": False,
         "hint": "the address you registered on the app; empty means this desk's Settings address"},
    ],
    "token_hint": "After the login the page jumps to your redirect address with code= in it; paste that value, or the whole address. The code is single use and lasts a few minutes.",
    "token_param": "code",
}

BASE = "https://api.upstox.com/v2"


def _redirect(cfg):
    got = (cfg.get("UPSTOX_REDIRECT_URI") or "").strip()
    return got or f"http://localhost:{os.getenv('DESK_PORT', '8765')}/settings"


def login_url(cfg):
    from urllib.parse import urlencode
    q = urlencode({"response_type": "code", "client_id": cfg["UPSTOX_API_KEY"],
                   "redirect_uri": _redirect(cfg)})
    return f"{BASE}/login/authorization/dialog?{q}"


def exchange_token(cfg, code):
    try:
        r = requests.post(BASE + "/login/authorization/token",
                          headers={"Accept": "application/json",
                                   "Content-Type": "application/x-www-form-urlencoded"},
                          data={"code": code, "client_id": cfg["UPSTOX_API_KEY"],
                                "client_secret": cfg["UPSTOX_API_SECRET"],
                                "redirect_uri": _redirect(cfg),
                                "grant_type": "authorization_code"},
                          timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Upstox: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    tok = j.get("access_token")
    if r.status_code != 200 or not tok:
        msg = ((j.get("errors") or [{}])[0].get("message") if isinstance(j.get("errors"), list) else None)
        raise BrokerError("Upstox did not accept that login: " + str(msg or j.get("message") or r.status_code)[:160]
                          + " The code is single use, so log in again for a fresh one.")
    return tok


def _get(client, path, **params):
    try:
        r = requests.get(BASE + path, headers=client["headers"], params=params, timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Upstox: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code in (401, 403):
        raise BrokerError("Upstox's session for today is not valid. Every token dies at 3:30 AM, so log in again from this screen.")
    if r.status_code != 200 or j.get("status") != "success":
        errs = j.get("errors") if isinstance(j.get("errors"), list) else []
        msg = errs[0].get("message") if errs else j.get("message")
        raise BrokerError("Upstox answered: " + str(msg or r.status_code)[:160])
    return j.get("data")


def connect(cfg, token=None):
    if not token:
        return None
    client = {"headers": {"Accept": "application/json", "Authorization": "Bearer " + token}}
    client["profile"] = _get(client, "/user/profile") or {}
    return client


def label(client):
    uid = str((client.get("profile") or {}).get("user_id") or "")
    return f"A/C ··{uid[-4:]}" if len(uid) >= 4 else "account"


def equity(client):
    rows = []
    for h in _get(client, "/portfolio/long-term-holdings") or []:
        exch = (h.get("exchange") or "NSE").upper()
        sym = h.get("trading_symbol") or h.get("tradingsymbol") or ""
        rows.append(derive({
            "code": sym, "name": h.get("company_name") or "", "exch": exch,
            "qty": num(h.get("quantity")), "avg": num(h.get("average_price")),
            "ltp": num(h.get("last_price")), "value": None,
            "pnl": num(h.get("pnl")), "pnl_pct": None,
            "day_pct": num(h.get("day_change_percentage")),
            "currency": "INR", "ysym": sym + (".BO" if exch.startswith("BSE") else ".NS"),
        }))
    return rows


def funds(client):
    # Since 19 July 2025 Upstox returns both segments combined in the equity block.
    d = _get(client, "/user/get-funds-and-margin") or {}
    eq = d.get("equity") or d.get("commodity") or {}
    return {"cash": num(eq.get("available_margin")), "currency": "INR",
            "buying_power": num(eq.get("available_margin"))}
