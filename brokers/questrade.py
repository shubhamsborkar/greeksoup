"""Questrade (Canada). Free, and open to any of its clients. The reader
registers a personal app on Questrade's site and it hands out one key. That key
is spent the moment it is used: Questrade returns a new one with every pass it
issues, so the desk saves the replacement each time and never asks again for as
long as it keeps reading. Three days off and Questrade forgets, so a fresh key
is pasted into Settings.

Questrade also names the server to talk to in the same answer, which is why
nothing here hard-codes an address for the reads. Reads /v1/accounts,
/v1/accounts/{id}/positions and /v1/accounts/{id}/balances. Positions carry the
price Questrade marks them at. Source: questrade.com/api/documentation.
Nothing here places a trade."""

import time

import requests

import brokers
from brokers import BrokerError, derive, last4, num

META = {
    "label": "Questrade",
    "where": "Canada",
    "region": "ca",
    "daily_login": False,
    "login_days": 3,
    "docs": "https://www.questrade.com/api/documentation/getting-started",
    "how": "questrade.com, App Hub: register a personal app with read access, then Generate new token. Paste that token below. The desk keeps the replacement Questrade sends back, so you only do this again after three days with the desk off.",
    "fields": [
        {"env": "QUESTRADE_REFRESH_TOKEN", "label": "Manual token", "secret": True,
         "hint": "from Generate new token on the App Hub; it is spent on first use"},
        {"env": "QUESTRADE_ACCOUNT", "label": "Account number", "required": False,
         "hint": "leave empty to use the first account on the login"},
    ],
}

LOGIN = "https://login.questrade.com/oauth2/token"


def _mint(token):
    """Swap a key for a pass, a server address and the next key."""
    try:
        r = requests.get(LOGIN, params={"grant_type": "refresh_token", "refresh_token": token},
                         timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Questrade: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code != 200 or not j.get("access_token"):
        raise BrokerError("Questrade did not accept that token: "
                          + str(j.get("message") or r.status_code)[:160])
    return j


def _adopt(client, j):
    client["access"] = j["access_token"]
    client["server"] = (j.get("api_server") or "").rstrip("/") + "/"
    client["expires"] = time.time() + float(j.get("expires_in") or 1800)
    if j.get("refresh_token"):
        client["refresh"] = j["refresh_token"]
        brokers.write_token(client["refresh"], "questrade")


def _access(client):
    if client.get("access") and time.time() < client.get("expires", 0) - 60:
        return client["access"]
    _adopt(client, _mint(client["refresh"]))
    return client["access"]


def _get(client, path):
    access = _access(client)
    try:
        r = requests.get(client["server"] + path, timeout=20,
                         headers={"Authorization": "Bearer " + access, "Accept": "application/json"})
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Questrade: " + str(exc)[:120]) from exc
    if r.status_code in (401, 403):
        raise BrokerError("Questrade refused that read. Generate a new token on the App Hub and save it here.")
    if r.status_code != 200:
        raise BrokerError(f"Questrade answered {r.status_code} for {path}.")
    return r.json() if r.content else {}


def connect(cfg, token=None):
    # The saved replacement first, the pasted one second: a token is spent on first use, so
    # the one in .env is dead as soon as the desk has read once.
    tried, last = [], None
    for candidate in (brokers.read_token("questrade"), (cfg.get("QUESTRADE_REFRESH_TOKEN") or "").strip()):
        if not candidate or candidate in tried:
            continue
        tried.append(candidate)
        client = {"refresh": candidate, "access": "", "expires": 0.0, "server": ""}
        try:
            _adopt(client, _mint(candidate))
        except BrokerError as exc:
            last = exc
            continue
        accounts = [str(a.get("number") or "") for a in (_get(client, "v1/accounts") or {}).get("accounts") or []]
        want = (cfg.get("QUESTRADE_ACCOUNT") or "").strip()
        if want and want not in accounts:
            raise BrokerError("No account with that number on this Questrade login.")
        if not accounts and not want:
            raise BrokerError("This Questrade login shows no account.")
        client["account"] = want or accounts[0]
        return client
    raise last or BrokerError("Questrade has no token to use. Generate one on the App Hub and save it here.")


def label(client):
    return last4(client.get("account"))


def equity(client):
    d = _get(client, f"v1/accounts/{client['account']}/positions")
    rows = []
    for p in (d or {}).get("positions") or []:
        sym = p.get("symbol") or ""
        rows.append(derive({
            "code": sym, "name": "", "exch": "", "qty": num(p.get("openQuantity")),
            "avg": num(p.get("averageEntryPrice")), "ltp": num(p.get("currentPrice")),
            "value": num(p.get("currentMarketValue")), "pnl": num(p.get("openPnl")),
            "pnl_pct": None, "day_pct": None,
            # Questrade already writes the symbol the way Yahoo does, THI.TO and AAPL alike.
            "currency": "CAD" if sym.endswith((".TO", ".VN")) else "USD", "ysym": sym,
        }))
    return rows


def funds(client):
    d = _get(client, f"v1/accounts/{client['account']}/balances") or {}
    rows = d.get("combinedBalances") or d.get("perCurrencyBalances") or []
    pick = next((b for b in rows if (b.get("currency") or "").upper() == "CAD"), None) or (rows[0] if rows else {})
    return {"cash": num(pick.get("cash")), "currency": (pick.get("currency") or "CAD").upper(),
            "buying_power": num(pick.get("buyingPower")), "equity": num(pick.get("totalEquity"))}
