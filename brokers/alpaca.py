"""Alpaca (United States). Key and secret from the Alpaca dashboard; a paper
account works the same way with its own keys. Reads /v2/account and
/v2/positions. Source: docs.alpaca.markets, Trading API reference."""

import requests

from brokers import BrokerError, derive, last4, num, pace, quote_result, quote_row, quotes_off, quotes_refused

META = {
    "label": "Alpaca",
    "where": "United States",
    "region": "us",
    "daily_login": False,
    "docs": "https://docs.alpaca.markets/",
    "how": "Alpaca's dashboard, under API keys: one key ID and one secret. A paper-trading account has its own pair; switch Paper on for it.",
    "fields": [
        {"env": "ALPACA_KEY", "label": "API key ID", "secret": True},
        {"env": "ALPACA_SECRET", "label": "API secret", "secret": True},
        {"env": "ALPACA_PAPER", "label": "Paper account", "switch": True, "required": False,
         "hint": "on for a paper-trading account, off for a live one"},
    ],
}


def _base(cfg):
    paper = (cfg.get("ALPACA_PAPER", "") or "").lower() in ("on", "1", "true", "yes")
    return "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"


def _headers(cfg):
    return {"APCA-API-KEY-ID": cfg["ALPACA_KEY"], "APCA-API-SECRET-KEY": cfg["ALPACA_SECRET"],
            "Accept": "application/json"}


def _get(client, path):
    r = requests.get(client["base"] + path, headers=client["headers"], timeout=20)
    if r.status_code in (401, 403):
        raise BrokerError("Alpaca did not accept these keys. Check them on the dashboard, and that Paper matches the account the keys belong to.")
    if r.status_code != 200:
        raise BrokerError(f"Alpaca answered {r.status_code} for {path}.")
    return r.json()


def connect(cfg, token=None):
    client = {"base": _base(cfg), "headers": _headers(cfg)}
    try:
        client["account"] = _get(client, "/v2/account")
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Alpaca: " + str(exc)[:120]) from exc
    return client


def label(client):
    return last4((client.get("account") or {}).get("account_number"))


def equity(client):
    rows = []
    for p in _get(client, "/v2/positions") or []:
        if str(p.get("asset_class", "")).lower() not in ("", "us_equity"):
            continue   # crypto and options positions are not the equity book
        plpc = num(p.get("unrealized_plpc"))
        chg = num(p.get("change_today"))
        rows.append(derive({
            "code": p.get("symbol"), "name": "", "exch": p.get("exchange") or "",
            "qty": num(p.get("qty")), "avg": num(p.get("avg_entry_price")),
            "ltp": num(p.get("current_price")), "value": num(p.get("market_value")),
            "pnl": num(p.get("unrealized_pl")),
            "pnl_pct": plpc * 100 if plpc is not None else None,
            "day_pct": chg * 100 if chg is not None else None,
            "currency": "USD", "ysym": p.get("symbol"),
        }))
    return rows


def funds(client):
    a = _get(client, "/v2/account")
    client["account"] = a
    return {"cash": num(a.get("cash")), "currency": a.get("currency") or "USD",
            "buying_power": num(a.get("buying_power")), "equity": num(a.get("equity"))}


DATA = "https://data.alpaca.markets"


def quote(client, code, exch=None):
    """A live price from the Market Data API, GET /v2/stocks/{symbol}/snapshot, with the same
    keys as the account. The free Basic plan serves the IEX exchange ("for equities only the
    IEX exchange"), which is the default feed for keys without the paid plan. The previous
    close is the previous daily bar's close."""
    if quotes_off(client):
        return None
    sym = str(code).upper()
    pace("alpaca-quote", 0.35)
    try:
        r = requests.get(f"{DATA}/v2/stocks/{sym}/snapshot", headers=client["headers"], timeout=10)
        j = r.json() if r.content else {}
    except (requests.RequestException, ValueError):
        return None
    if r.status_code == 403:
        return quotes_refused(client)
    if r.status_code != 200:
        return quote_result(client, None) if r.status_code != 401 else None
    t, q, d = j.get("latestTrade") or {}, j.get("latestQuote") or {}, j.get("dailyBar") or {}
    book = {"buy": [{"price": q.get("bp"), "quantity": q.get("bs")}], "sell": [{"price": q.get("ap"), "quantity": q.get("as")}]}
    return quote_result(client, quote_row(code, exch or "US", t.get("p"), (j.get("prevDailyBar") or {}).get("c"),
                                          d.get("o"), d.get("h"), d.get("l"), book, d.get("v")))
