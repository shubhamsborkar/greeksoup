"""Charles Schwab (United States), through the Trader API. An app key and
secret from developer.schwab.com, on an app with the Accounts and Trading
product, which Schwab approves by hand before it works. The login is a weekly
one, not a daily one: Schwab's sign-in hands back a code, the desk turns that
into a key that lasts seven days, and works out a fresh half-hour pass from it
on its own for as long as the week lasts. Schwab's callback address has to be
an https one, so the reader pastes the address the browser lands on rather than
having it arrive here by itself; the page it lands on is usually blank, and the
address is still the right one.

Reads /trader/v1/accounts/accountNumbers and /trader/v1/accounts with the
positions field. Positions carry the market value, so the desk prices the book
from Schwab and not from Yahoo. Contracts are left out: this desk's book is
shares. Source: developer.schwab.com. Nothing in this file places a trade."""

import base64
import time
from urllib.parse import parse_qs, unquote, urlparse

import requests

from brokers import BrokerError, derive, last4, num

META = {
    "label": "Charles Schwab",
    "where": "United States",
    "region": "us",
    "daily_login": True,
    "login_days": 7,
    "docs": "https://developer.schwab.com/",
    "prices": "Live prices: the desk reads your Schwab holdings and prices your watchlist from the free feed for now. Schwab's Trader API has a market data product, so your agent can add live prices to this broker's file from Schwab's developer documentation, which you read signed in to your Schwab developer account.",
    "how": "developer.schwab.com: create an app, add the Accounts and Trading product, and set its callback address (it has to start with https, and https://127.0.0.1 is allowed). Schwab approves the app by hand, which takes a day or two; when it says Ready for Use, copy the app key and secret. Then sign in once a week from this screen.",
    "fields": [
        {"env": "SCHWAB_APP_KEY", "label": "App key", "secret": True},
        {"env": "SCHWAB_APP_SECRET", "label": "App secret", "secret": True},
        {"env": "SCHWAB_CALLBACK", "label": "Callback address", "required": False,
         "hint": "exactly as it reads on the app; empty means https://127.0.0.1"},
    ],
    "token_hint": "Sign in, then press Done. The page that follows is often blank or says the site cannot be reached; its address is what you paste here, whole. Schwab's key lasts seven days, so this is a weekly job.",
    "token_param": "code",
}

AUTH = "https://api.schwabapi.com/v1/oauth"
BASE = "https://api.schwabapi.com/trader/v1"


def _callback(cfg):
    return (cfg.get("SCHWAB_CALLBACK") or "").strip() or "https://127.0.0.1"


def login_url(cfg):
    from urllib.parse import urlencode
    q = urlencode({"client_id": cfg["SCHWAB_APP_KEY"], "redirect_uri": _callback(cfg),
                   "response_type": "code"})
    return f"{AUTH}/authorize?{q}"


def _token_call(cfg, form):
    basic = base64.b64encode(f"{cfg['SCHWAB_APP_KEY']}:{cfg['SCHWAB_APP_SECRET']}".encode()).decode()
    try:
        r = requests.post(AUTH + "/token",
                          headers={"Authorization": "Basic " + basic,
                                   "Content-Type": "application/x-www-form-urlencoded"},
                          data=form, timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Schwab: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code != 200:
        raise BrokerError("Schwab did not accept that sign-in: "
                          + str(j.get("error_description") or j.get("error") or r.status_code)[:160]
                          + " A sign-in code is single use and the week's key lasts seven days.")
    return j


def _code_from(raw):
    """The code, from the whole address the browser landed on or from the value alone.
    Schwab's code is percent-encoded and ends in @, so it is decoded, never cut."""
    raw = (raw or "").strip()
    if "code=" in raw:
        qs = parse_qs(urlparse(raw).query if "://" in raw else raw)
        got = (qs.get("code") or [""])[0]
        if got:
            return got
    return unquote(raw)


def exchange_token(cfg, raw):
    j = _token_call(cfg, {"grant_type": "authorization_code", "code": _code_from(raw),
                          "redirect_uri": _callback(cfg)})
    tok = j.get("refresh_token")
    if not tok:
        raise BrokerError("Schwab signed in but handed back no week key.")
    return tok


def _access(client):
    """A live half-hour pass, made fresh from the week's key when the last one is spent."""
    if client.get("access") and time.time() < client.get("expires", 0) - 60:
        return client["access"]
    j = _token_call(client["cfg"], {"grant_type": "refresh_token", "refresh_token": client["refresh"]})
    if not j.get("access_token"):
        raise BrokerError("Schwab's week key is spent. Sign in again from this screen.")
    client["access"] = j["access_token"]
    client["expires"] = time.time() + float(j.get("expires_in") or 1800)
    return client["access"]


def _get(client, path, **params):
    try:
        r = requests.get(BASE + path, params=params, timeout=20,
                         headers={"Authorization": "Bearer " + _access(client),
                                  "Accept": "application/json"})
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Schwab: " + str(exc)[:120]) from exc
    if r.status_code in (401, 403):
        raise BrokerError("Schwab refused that read. The week's key may be spent, or the app may not carry the Accounts and Trading product yet.")
    if r.status_code != 200:
        raise BrokerError(f"Schwab answered {r.status_code} for {path}.")
    return r.json() if r.content else []


def connect(cfg, token=None):
    if not token:
        return None
    client = {"cfg": cfg, "refresh": token, "access": "", "expires": 0.0}
    nums = _get(client, "/accounts/accountNumbers")
    client["accounts"] = nums if isinstance(nums, list) else []
    if not client["accounts"]:
        raise BrokerError("Schwab shows no account on this sign-in.")
    return client


def label(client):
    return last4((client.get("accounts") or [{}])[0].get("accountNumber"))


def _first_account(client):
    d = _get(client, "/accounts", fields="positions")
    for a in d if isinstance(d, list) else []:
        sa = a.get("securitiesAccount") or {}
        if sa:
            return sa
    return {}


def equity(client):
    rows = []
    for p in _first_account(client).get("positions") or []:
        ins = p.get("instrument") or {}
        if (ins.get("assetType") or "").upper() == "OPTION":
            continue
        qty = (num(p.get("longQuantity")) or 0) - (num(p.get("shortQuantity")) or 0)
        if not qty:
            continue
        mv = num(p.get("marketValue"))
        sym = ins.get("symbol") or ""
        rows.append(derive({
            "code": sym, "name": ins.get("description") or "", "exch": "",
            "qty": qty, "avg": num(p.get("averagePrice")),
            "ltp": (mv / qty) if mv is not None else None, "value": mv,
            "pnl": num(p.get("longOpenProfitLoss")), "pnl_pct": None,
            "day_pct": num(p.get("currentDayProfitLossPercentage")),
            "currency": "USD", "ysym": sym,
        }))
    return rows


def funds(client):
    bal = _first_account(client).get("currentBalances") or {}
    return {"cash": num(bal.get("cashBalance")), "currency": "USD",
            "buying_power": num(bal.get("buyingPower")) or num(bal.get("availableFunds")),
            "equity": num(bal.get("liquidationValue"))}
