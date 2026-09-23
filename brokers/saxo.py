"""Saxo Bank, through OpenAPI. A Danish bank whose clients sit across Europe,
Asia and the Middle East, and whose accounts reach most of the world's
exchanges from one login. An app key and secret from developer.saxo, then a
login from this screen: Saxo's sign-in hands back a code, the desk turns it
into a key, and mints a fresh twenty-minute pass from it while the desk runs.
Saxo replaces that key every time it is used, so the desk saves the new one
each time; leave the desk off for a day and the login comes round again.

Reads /port/v1/accounts/me, /port/v1/netpositions/me and /port/v1/balances/me.
Net positions carry the price Saxo marks them at, so the book is priced from
the bank. Only the cash equity lines are read into the book: a Saxo account can
also hold currency and contracts for difference, which are not what this desk
is for. Source: developer.saxo/openapi. Nothing here places a trade."""

import base64
import os
import time
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import requests

import brokers
from brokers import BrokerError, derive, last4, num

META = {
    "label": "Saxo Bank",
    "where": "Europe, Asia and the Middle East",
    "region": "us",
    "daily_login": True,
    "docs": "https://www.developer.saxo/openapi/learn",
    "how": "developer.saxo: create an application on the live environment, set its redirect address to this desk's Settings address, and copy the app key and secret. Switch Simulation on to point the same keys at Saxo's practice system.",
    "fields": [
        {"env": "SAXO_APP_KEY", "label": "App key", "secret": True},
        {"env": "SAXO_APP_SECRET", "label": "App secret", "secret": True},
        {"env": "SAXO_REDIRECT_URI", "label": "Redirect address", "required": False,
         "hint": "as registered on the app; empty means this desk's Settings address"},
        {"env": "SAXO_SIM", "label": "Simulation account", "switch": True, "required": False,
         "hint": "on for Saxo's practice system"},
    ],
    "token_hint": "After the sign-in the page jumps to your redirect address with code= in it; paste that value, or the whole address.",
    "token_param": "code",
}

# Saxo's symbols read AAPL:xnas, the exchange being the market's own code. Yahoo writes the
# same share with a suffix, and none for the United States.
SUFFIX = {"xnas": "", "xnys": "", "arcx": "", "bats": "", "xase": "",
          "xlon": ".L", "xcse": ".CO", "xsto": ".ST", "xosl": ".OL", "xhel": ".HE",
          "xetr": ".DE", "xams": ".AS", "xbru": ".BR", "xpar": ".PA", "xlis": ".LS",
          "xmil": ".MI", "xmad": ".MC", "xswx": ".SW", "xvtx": ".SW", "xwbo": ".VI",
          "xwar": ".WA", "xpra": ".PR", "xtse": ".TO", "xtsx": ".V",
          "xhkg": ".HK", "xtks": ".T", "xses": ".SI", "xasx": ".AX",
          "xnse": ".NS", "xbom": ".BO", "xjse": ".JO"}
CASH_EQUITY = {"stock", "etf", "etc", "etn", "fund", "stockindex"}


def _sim(cfg):
    return (cfg.get("SAXO_SIM", "") or "").lower() in ("on", "1", "true", "yes")


def _auth_host(cfg):
    return "https://sim.logonvalidation.net" if _sim(cfg) else "https://live.logonvalidation.net"


def _gateway(cfg):
    return ("https://gateway.saxobank.com/sim/openapi" if _sim(cfg)
            else "https://gateway.saxobank.com/openapi")


def _redirect(cfg):
    got = (cfg.get("SAXO_REDIRECT_URI") or "").strip()
    return got or f"http://localhost:{os.getenv('DESK_PORT', '8765')}/settings"


def login_url(cfg):
    q = urlencode({"response_type": "code", "client_id": cfg["SAXO_APP_KEY"],
                   "redirect_uri": _redirect(cfg), "state": "desk"})
    return f"{_auth_host(cfg)}/authorize?{q}"


def _token_call(cfg, form):
    basic = base64.b64encode(f"{cfg['SAXO_APP_KEY']}:{cfg['SAXO_APP_SECRET']}".encode()).decode()
    try:
        r = requests.post(_auth_host(cfg) + "/token",
                          headers={"Authorization": "Basic " + basic,
                                   "Content-Type": "application/x-www-form-urlencoded"},
                          data={**form, "redirect_uri": _redirect(cfg)}, timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Saxo: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code != 200:
        raise BrokerError("Saxo did not accept that sign-in: "
                          + str(j.get("error_description") or j.get("error") or r.status_code)[:160]
                          + " A sign-in code is single use, and Saxo's key is short lived.")
    return j


def exchange_token(cfg, raw):
    raw = (raw or "").strip()
    code = raw
    if "code=" in raw:
        code = (parse_qs(urlparse(raw).query if "://" in raw else raw).get("code") or [""])[0] or raw
    j = _token_call(cfg, {"grant_type": "authorization_code", "code": unquote(code)})
    tok = j.get("refresh_token")
    if not tok:
        raise BrokerError("Saxo signed in but handed back no key to keep.")
    return tok


def _access(client):
    """A live twenty-minute pass. Saxo hands back a new key each time, so it is saved."""
    if client.get("access") and time.time() < client.get("expires", 0) - 60:
        return client["access"]
    j = _token_call(client["cfg"], {"grant_type": "refresh_token", "refresh_token": client["refresh"]})
    if not j.get("access_token"):
        raise BrokerError("Saxo's key is spent. Sign in again from this screen.")
    client["access"] = j["access_token"]
    client["expires"] = time.time() + float(j.get("expires_in") or 1200)
    if j.get("refresh_token") and j["refresh_token"] != client["refresh"]:
        client["refresh"] = j["refresh_token"]
        brokers.write_token(client["refresh"], "saxo")
    return client["access"]


def _get(client, path, **params):
    try:
        r = requests.get(_gateway(client["cfg"]) + path, params=params, timeout=25,
                         headers={"Authorization": "Bearer " + _access(client),
                                  "Accept": "application/json"})
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Saxo: " + str(exc)[:120]) from exc
    if r.status_code in (401, 403):
        raise BrokerError("Saxo refused that read. The key may be spent, or the app may not be the one this account belongs to.")
    if r.status_code != 200:
        raise BrokerError(f"Saxo answered {r.status_code} for {path}.")
    return r.json() if r.content else {}


def connect(cfg, token=None):
    if not token:
        return None
    client = {"cfg": cfg, "refresh": token, "access": "", "expires": 0.0}
    rows = (_get(client, "/port/v1/accounts/me") or {}).get("Data") or []
    if not rows:
        raise BrokerError("Saxo shows no account on this sign-in.")
    client["account"] = str(rows[0].get("AccountId") or rows[0].get("AccountKey") or "")
    return client


def label(client):
    return last4(client.get("account"))


def _ysym(symbol):
    sym = (symbol or "").split(":")
    base = sym[0].replace("$", "-")
    if len(sym) < 2:
        return base
    return base + SUFFIX.get(sym[1].lower(), "")


def equity(client):
    d = _get(client, "/port/v1/netpositions/me",
             FieldGroups="NetPositionBase,NetPositionView,DisplayAndFormat")
    rows = []
    for p in (d or {}).get("Data") or []:
        base, view = p.get("NetPositionBase") or {}, p.get("NetPositionView") or {}
        fmt = p.get("DisplayAndFormat") or {}
        if (base.get("AssetType") or "").lower() not in CASH_EQUITY:
            continue                      # currency and contracts for difference are not this book
        qty = num(base.get("Amount"))
        if (base.get("OpeningDirection") or "").lower() == "short" and qty:
            qty = -abs(qty)
        sym = fmt.get("Symbol") or p.get("NetPositionId") or ""
        rows.append(derive({
            "code": sym, "name": fmt.get("Description") or "",
            "exch": (sym.split(":")[1].upper() if ":" in sym else ""),
            "qty": qty, "avg": num(view.get("AverageOpenPrice")),
            "ltp": num(view.get("CurrentPrice")), "value": num(view.get("MarketValue")),
            "pnl": num(view.get("ProfitLossOnTrade")), "pnl_pct": None,
            "day_pct": num(view.get("InstrumentPriceDayPercentChange")),
            "currency": fmt.get("Currency") or "", "ysym": _ysym(sym),
        }))
    return rows


def funds(client):
    b = _get(client, "/port/v1/balances/me") or {}
    return {"cash": num(b.get("CashBalance")), "currency": b.get("Currency") or "",
            "buying_power": num(b.get("MarginAvailableForTrading")) or num(b.get("CashAvailableForTrading")),
            "equity": num(b.get("TotalValue"))}
