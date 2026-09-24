"""Tradier (United States). One access token from the Tradier dashboard. Reads
/v1/user/profile for the account number, /v1/accounts/{id}/positions and
/v1/accounts/{id}/balances. Positions carry cost basis and quantity but no
price, so the desk marks them from Yahoo. Source: docs.tradier.com."""

import requests

from brokers import BrokerError, derive, last4, num, pace, quote_result, quote_row, quotes_off

META = {
    "label": "Tradier",
    "where": "United States",
    "region": "us",
    "daily_login": False,
    "docs": "https://docs.tradier.com/",
    "how": "Tradier's dashboard, under API access: one access token. The sandbox (paper) account has its own token; switch Sandbox on for it.",
    "fields": [
        {"env": "TRADIER_TOKEN", "label": "Access token", "secret": True},
        {"env": "TRADIER_ACCOUNT", "label": "Account number", "required": False,
         "hint": "leave empty to use the first account on the profile"},
        {"env": "TRADIER_SANDBOX", "label": "Sandbox account", "switch": True, "required": False,
         "hint": "on for the paper-trading sandbox"},
    ],
}


def _base(cfg):
    sb = (cfg.get("TRADIER_SANDBOX", "") or "").lower() in ("on", "1", "true", "yes")
    return "https://sandbox.tradier.com" if sb else "https://api.tradier.com"


def _get(client, path, **params):
    r = requests.get(client["base"] + path, headers=client["headers"], params=params, timeout=20)
    if r.status_code in (401, 403):
        raise BrokerError("Tradier did not accept this token. Check it on the dashboard, and that Sandbox matches the account it belongs to.")
    if r.status_code != 200:
        raise BrokerError(f"Tradier answered {r.status_code} for {path}.")
    return r.json()


def _as_list(v):
    if v in (None, "null", ""):
        return []
    return v if isinstance(v, list) else [v]


def connect(cfg, token=None):
    client = {"base": _base(cfg),
              "headers": {"Authorization": "Bearer " + cfg["TRADIER_TOKEN"], "Accept": "application/json"}}
    try:
        prof = _get(client, "/v1/user/profile")
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Tradier: " + str(exc)[:120]) from exc
    accounts = _as_list(((prof or {}).get("profile") or {}).get("account"))
    want = (cfg.get("TRADIER_ACCOUNT") or "").strip()
    chosen = None
    for a in accounts:
        if not want or str(a.get("account_number")) == want:
            chosen = a
            break
    if not chosen:
        raise BrokerError("No account with that number on this Tradier profile." if want else "This Tradier profile has no account.")
    client["account"] = str(chosen.get("account_number"))
    return client


def label(client):
    return last4(client.get("account"))


def equity(client):
    d = _get(client, f"/v1/accounts/{client['account']}/positions")
    rows = []
    for p in _as_list(((d or {}).get("positions") or {}).get("position") if isinstance(d.get("positions"), dict) else None):
        qty = num(p.get("quantity"))
        cost = num(p.get("cost_basis"))
        avg = cost / qty if (cost is not None and qty) else None
        sym = str(p.get("symbol") or "")
        if len(sym) > 12:
            continue   # an option symbol (OCC style), not a share
        rows.append(derive({
            "code": sym, "name": "", "exch": "", "qty": qty, "avg": avg,
            "ltp": None, "value": None, "pnl": None, "pnl_pct": None, "day_pct": None,
            "currency": "USD", "ysym": sym,
        }))
    return rows


def funds(client):
    b = (_get(client, f"/v1/accounts/{client['account']}/balances") or {}).get("balances") or {}
    bp = None
    for k in ("margin", "cash", "pdt"):
        sub = b.get(k) or {}
        bp = num(sub.get("stock_buying_power")) or num(sub.get("cash_available")) or bp
    return {"cash": num(b.get("total_cash")), "currency": "USD", "buying_power": bp,
            "equity": num(b.get("total_equity"))}


def quote(client, code, exch=None):
    """A live price from GET /v1/markets/quotes. Real-time for Tradier Brokerage account
    holders; the sandbox is fifteen minutes late. Market data allows 120 calls a minute."""
    if quotes_off(client):
        return None
    pace("tradier-quote", 0.55)
    try:
        r = requests.get(client["base"] + "/v1/markets/quotes", headers=client["headers"],
                         params={"symbols": str(code).upper()}, timeout=10)
        j = r.json() if r.content else {}
    except (requests.RequestException, ValueError):
        return None
    if r.status_code in (401, 403):
        return None
    if r.status_code != 200:
        return quote_result(client, None)
    rows = _as_list(((j.get("quotes") or {}).get("quote")))
    q = rows[0] if rows else {}
    book = {"buy": [{"price": q.get("bid"), "quantity": q.get("bidsize")}], "sell": [{"price": q.get("ask"), "quantity": q.get("asksize")}]}
    return quote_result(client, quote_row(code, exch or "US", q.get("last"), q.get("prevclose"),
                                          q.get("open"), q.get("high"), q.get("low"), book, q.get("volume")))
