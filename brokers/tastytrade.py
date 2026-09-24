"""tastytrade (United States). Free for its clients. The reader makes an OAuth
grant on tastytrade's own site, which hands out a client secret and a key that
does not expire; the desk turns that into a fifteen-minute pass whenever it
needs one, so there is nothing to paste each day. tastytrade rejects any
request without a User-Agent, so the desk names itself on every call.

Reads /customers/me/accounts, /accounts/{number}/positions and
/accounts/{number}/balances. Positions carry the cost and the closing mark, so
the desk works the line's price out from what tastytrade reports and falls back
to Yahoo when it reports none. Option legs are left out: this desk's book is
shares. Source: developer.tastytrade.com. Nothing here places a trade."""

import time

import requests

from brokers import BrokerError, derive, last4, num, pace, quote_result, quote_row, quotes_off, quotes_refused

META = {
    "label": "tastytrade",
    "where": "United States",
    "region": "us",
    "daily_login": False,
    "docs": "https://developer.tastytrade.com/",
    "how": "tastytrade's site, under OAuth Applications: create an application, then Manage and Create Grant. That hands you a client secret and a refresh token, which do not expire. Switch Sandbox on for the practice system, which has keys of its own.",
    "fields": [
        {"env": "TASTY_CLIENT_SECRET", "label": "Client secret", "secret": True},
        {"env": "TASTY_REFRESH_TOKEN", "label": "Refresh token", "secret": True,
         "hint": "from Create Grant on the same page"},
        {"env": "TASTY_ACCOUNT", "label": "Account number", "required": False,
         "hint": "leave empty to use the first account on the login"},
        {"env": "TASTY_SANDBOX", "label": "Sandbox account", "switch": True, "required": False},
    ],
}

AGENT = "greeksoup-desk/1.0"


def _base(cfg):
    sb = (cfg.get("TASTY_SANDBOX", "") or "").lower() in ("on", "1", "true", "yes")
    return "https://api.cert.tastyworks.com" if sb else "https://api.tastyworks.com"


def _access(client):
    """A fifteen-minute pass. The refresh token behind it is not replaced and does not expire."""
    if client.get("access") and time.time() < client.get("expires", 0) - 60:
        return client["access"]
    cfg = client["cfg"]
    try:
        r = requests.post(_base(cfg) + "/oauth/token", timeout=20,
                          headers={"User-Agent": AGENT, "Content-Type": "application/json"},
                          json={"grant_type": "refresh_token",
                                "refresh_token": cfg["TASTY_REFRESH_TOKEN"],
                                "client_secret": cfg["TASTY_CLIENT_SECRET"]})
    except requests.RequestException as exc:
        raise BrokerError("Could not reach tastytrade: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code != 200 or not j.get("access_token"):
        raise BrokerError("tastytrade did not accept these keys: "
                          + str(j.get("error_description") or j.get("error") or r.status_code)[:160]
                          + " Check that the grant is the live one and not the sandbox, and that Sandbox above matches.")
    client["access"] = j["access_token"]
    client["expires"] = time.time() + float(j.get("expires_in") or 900)
    return client["access"]


def _get(client, path):
    try:
        r = requests.get(_base(client["cfg"]) + path, timeout=20,
                         headers={"User-Agent": AGENT, "Accept": "application/json",
                                  "Authorization": "Bearer " + _access(client)})
    except requests.RequestException as exc:
        raise BrokerError("Could not reach tastytrade: " + str(exc)[:120]) from exc
    if r.status_code in (401, 403):
        raise BrokerError("tastytrade refused that read. The grant may have been revoked on their site.")
    if r.status_code != 200:
        raise BrokerError(f"tastytrade answered {r.status_code} for {path}.")
    j = r.json() if r.content else {}
    return (j or {}).get("data") or {}


def connect(cfg, token=None):
    client = {"cfg": cfg, "access": "", "expires": 0.0}
    want = (cfg.get("TASTY_ACCOUNT") or "").strip()
    numbers = []
    for item in (_get(client, "/customers/me/accounts") or {}).get("items") or []:
        acct = item.get("account") or item
        got = str(acct.get("account-number") or "")
        if got:
            numbers.append(got)
    if want and want not in numbers:
        raise BrokerError("No account with that number on this tastytrade login.")
    if not numbers and not want:
        raise BrokerError("This tastytrade login shows no account.")
    client["account"] = want or numbers[0]
    return client


def label(client):
    return last4(client.get("account"))


def equity(client):
    d = _get(client, f"/accounts/{client['account']}/positions")
    rows = []
    for p in (d or {}).get("items") or []:
        if (p.get("instrument-type") or "").lower() != "equity":
            continue                       # option and future legs are not this book
        qty = num(p.get("quantity")) or 0
        if (p.get("quantity-direction") or "").lower() == "short":
            qty = -abs(qty)
        if not qty:
            continue
        sym = p.get("symbol") or ""
        rows.append(derive({
            "code": sym, "name": "", "exch": "", "qty": qty,
            "avg": num(p.get("average-open-price")), "ltp": num(p.get("close-price")),
            "value": None, "pnl": None, "pnl_pct": None, "day_pct": None,
            "currency": "USD", "ysym": sym,
        }))
    return rows


def funds(client):
    b = _get(client, f"/accounts/{client['account']}/balances") or {}
    return {"cash": num(b.get("cash-balance")), "currency": b.get("currency") or "USD",
            "buying_power": num(b.get("equity-buying-power")),
            "equity": num(b.get("net-liquidating-value"))}


def quote(client, code, exch=None):
    """A live price from GET /market-data/by-type?equity=. tastytrade serves it to funded
    accounts only ("no delayed quotes are served over REST"); a refusal switches prices off
    for the session and the desk uses the free feed. Keys come dasherized, prices as text."""
    if quotes_off(client):
        return None
    pace("tasty-quote", 0.5)
    try:
        r = requests.get(_base(client["cfg"]) + "/market-data/by-type", timeout=10,
                         params={"equity": str(code).upper()},
                         headers={"User-Agent": AGENT, "Accept": "application/json",
                                  "Authorization": "Bearer " + _access(client)})
        j = r.json() if r.content else {}
    except (requests.RequestException, ValueError, BrokerError):
        return None
    if r.status_code == 403:
        return quotes_refused(client)
    if r.status_code != 200:
        return quote_result(client, None) if r.status_code != 401 else None
    rows = ((j.get("data") or {}).get("items")) or []
    q = rows[0] if rows else {}
    book = {"buy": [{"price": q.get("bid"), "quantity": q.get("bid-size")}], "sell": [{"price": q.get("ask"), "quantity": q.get("ask-size")}]}
    return quote_result(client, quote_row(code, exch or "US", q.get("last"), q.get("prev-close"), q.get("open"),
                                          q.get("day-high-price"), q.get("day-low-price"), book, q.get("volume")))
