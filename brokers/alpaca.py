"""Alpaca (United States). Key and secret from the Alpaca dashboard; a paper
account works the same way with its own keys. Reads /v2/account and
/v2/positions. Source: docs.alpaca.markets, Trading API reference."""

import requests

from brokers import BrokerError, derive, last4, num

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
