"""Trading 212 (United Kingdom and Europe). An API key and secret generated in
the app (Settings, API). Basic authentication, key as the user name and secret
as the password. Reads /api/v0/equity/account/cash, /api/v0/equity/account/info
and /api/v0/equity/positions. The API is marked beta by Trading 212 and the
position shape has changed once already, so both shapes are read. Source:
docs.trading212.com and the Trading 212 help centre."""

import base64

import requests

from brokers import BrokerError, derive, last4, num

META = {
    "label": "Trading 212",
    "where": "United Kingdom, Europe",
    "region": "us",
    "daily_login": False,
    "docs": "https://docs.trading212.com/api",
    "how": "In the Trading 212 app: menu, Settings, API, Generate API key, with the account-data and portfolio permissions. You get a key and a secret. Invest and ISA accounts only.",
    "fields": [
        {"env": "T212_KEY", "label": "API key", "secret": True},
        {"env": "T212_SECRET", "label": "API secret", "secret": True},
        {"env": "T212_DEMO", "label": "Practice account", "switch": True, "required": False,
         "hint": "on for the practice (demo) account"},
    ],
}


def _base(cfg):
    demo = (cfg.get("T212_DEMO", "") or "").lower() in ("on", "1", "true", "yes")
    return "https://demo.trading212.com/api/v0" if demo else "https://live.trading212.com/api/v0"


def _get(client, path):
    r = requests.get(client["base"] + path, headers=client["headers"], timeout=20)
    if r.status_code in (401, 403):
        raise BrokerError("Trading 212 did not accept the key and secret. Check them in the app, and that Practice matches the account they belong to.")
    if r.status_code == 429:
        raise BrokerError("Trading 212 asked the desk to slow down; it retries on the next refresh.")
    if r.status_code != 200:
        raise BrokerError(f"Trading 212 answered {r.status_code} for {path}.")
    return r.json()


def connect(cfg, token=None):
    cred = base64.b64encode(f"{cfg['T212_KEY']}:{cfg['T212_SECRET']}".encode()).decode()
    client = {"base": _base(cfg), "headers": {"Authorization": "Basic " + cred, "Accept": "application/json"}}
    try:
        client["cash"] = _get(client, "/equity/account/cash")
        try:
            client["info"] = _get(client, "/equity/account/info")
        except BrokerError:
            client["info"] = {}
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Trading 212: " + str(exc)[:120]) from exc
    return client


def label(client):
    return last4((client.get("info") or {}).get("id"))


def _ysym(ticker):
    """Trading 212 tickers look like AAPL_US_EQ or RR_EQ (an LSE line). Yahoo's
    symbol for the first is AAPL; a London line gets the .L suffix."""
    t = str(ticker or "")
    if t.endswith("_US_EQ"):
        return t[:-6]
    if t.endswith("_EQ"):
        return t[:-3].replace("l", "") + ".L"
    return t


def equity(client):
    rows = []
    for p in _get(client, "/equity/positions") or []:
        inst = p.get("instrument") or {}
        ticker = inst.get("ticker") or p.get("ticker")
        wallet = p.get("walletImpact") or {}
        rows.append(derive({
            "code": ticker, "name": inst.get("name") or "", "exch": "",
            "qty": num(p.get("quantity")),
            "avg": num(p.get("averagePricePaid")) if p.get("averagePricePaid") is not None else num(p.get("averagePrice")),
            "ltp": num(p.get("currentPrice")),
            "value": num(wallet.get("currentValue")),
            "pnl": num(wallet.get("unrealizedProfitLoss")) if wallet else num(p.get("ppl")),
            "pnl_pct": None, "day_pct": None,
            "currency": inst.get("currency") or (client.get("info") or {}).get("currencyCode") or "",
            "ysym": _ysym(ticker),
        }))
    return rows


def funds(client):
    c = _get(client, "/equity/account/cash") or {}
    client["cash"] = c
    return {"cash": num(c.get("free")), "currency": (client.get("info") or {}).get("currencyCode") or "",
            "buying_power": num(c.get("free")), "equity": num(c.get("total"))}
