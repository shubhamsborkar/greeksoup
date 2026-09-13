"""The broker layer. One file per broker, all read-only, all the same shape.

The reader picks a broker on the Settings screen; the desk reads that broker's
account through the matching file here. Nothing in this folder places an order.

Every adapter module has:
  META                      id, label, where (plain words), fields (what the
                            reader pastes), daily_login (True when the broker's
                            regulator wants a fresh login every trading day),
                            region (the market file in markets/ that supplies
                            the session, the index and the currency), docs
  connect(cfg, token=None)  -> a client object, or raises BrokerError(plain words)
  label(client)             -> "A/C ··1234" (last four of the account, never a name)
  equity(client)            -> [row, ...]   see ROW below
  funds(client)             -> {"cash": float, "currency": "USD", "buying_power": float or None}
optional (README.md lists each one's shape; the desk shows what a file has):
  login_url, exchange_token           daily-login brokers
  futures, quote, history, intraday,  what the broker's feed serves beyond holdings
  futures_quote, sparks, tape, stream, stream_healthy
  resolve, search                     a symbol master, when broker codes differ from
                                      exchange symbols
  extra_accounts, commodities_local   several accounts; local commodity reads

ROW (one holding):
  code       the broker's own symbol         name    company name if the broker gives it
  exch       exchange, if known               qty     shares (float)
  avg        average cost per share           ltp     last price; None when the broker
                                                      does not give one (the desk fills
                                                      it from Yahoo through ysym)
  value, pnl, pnl_pct, day_pct               derived when possible, else None
  currency   "USD", "INR", "GBP" ...
  ysym       the Yahoo Finance symbol for the same share (AAPL, RELIANCE.NS, RR.L)

cfg is a dict of the adapter's fields read from the environment (.env).
"""

import importlib
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Alphabetical by label. Adding a broker = one file here + one line in this list.
REGISTRY = ["alpaca", "icici_breeze", "ibkr_flex", "tradier", "trading212", "zerodha_kite"]

# Brokers the desk knows about but does not ship a file for, and the honest path
# for each. Shown on the Settings screen under "Another broker".
OTHERS = [
    ("Charles Schwab", "Has an API for individuals. The login has to be repeated every seven days, so your agent writes this one from Schwab's documentation and keeps the weekly login."),
    ("Fidelity, Vanguard", "No API for individuals. Export the holdings to a file and paste them into Desk · Book; most exports paste straight in."),
    ("Robinhood", "No API for stocks. Export the holdings into Desk · Book, or have your agent connect Robinhood's own agent server."),
    ("Upstox, Angel One, Groww", "Each has an API with a daily login, the same pattern as the two Indian brokers shipped here, and the same market file serves all of them. Your agent writes it from their documentation."),
    ("Any other broker", "If it publishes an API, your agent writes the file from its documentation; the shape it has to return is in brokers/README.md. If it does not, Desk · Book takes an export."),
]


class BrokerError(Exception):
    """Plain words for the reader. Never a stack trace."""


def load(broker_id):
    if broker_id not in REGISTRY:
        return None
    return importlib.import_module(f"brokers.{broker_id}")


def all_meta():
    out = []
    for bid in REGISTRY:
        m = dict(load(bid).META)
        m["id"] = bid
        out.append(m)
    return out


def active_id():
    """The broker the reader chose. A copy set up before the picker existed has
    one broker's keys and no BROKER line; the first configured file counts."""
    bid = (os.getenv("BROKER", "") or "").strip().lower()
    if bid in REGISTRY:
        return bid
    if bid in ("", "none"):
        for cand in REGISTRY:
            if configured(cand):
                return cand
    return ""


def config(broker_id):
    m = load(broker_id)
    if not m:
        return {}
    return {f["env"]: (os.getenv(f["env"], "") or "").strip() for f in m.META["fields"]}


def configured(broker_id):
    m = load(broker_id)
    if not m:
        return False
    cfg = config(broker_id)
    for f in m.META["fields"]:
        v = cfg.get(f["env"], "")
        if f.get("required", True) and (not v or v.startswith(("your_", "paste_"))):
            return False
    return True


# ---- today's token for daily-login brokers -----------------------------------
# One file, session_token_primary.txt, a date line then the token; gitignored.
TOKEN_PATH = os.path.join(ROOT, "session_token_primary.txt")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def read_token():
    try:
        with open(TOKEN_PATH, encoding="utf-8") as fh:
            date_line = fh.readline().strip()
            token = fh.readline().strip()
    except OSError:
        return None
    return token if (date_line == _today() and token) else None


def write_token(token):
    with open(TOKEN_PATH, "w", encoding="utf-8") as fh:
        fh.write(f"{_today()}\n{token}\n")


def clear_token():
    try:
        os.remove(TOKEN_PATH)
    except OSError:
        pass


# ---- helpers shared by the adapters ------------------------------------------
def num(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def derive(row):
    """Fill value, pnl and pnl_pct from qty, avg and ltp when they are missing."""
    qty, avg, ltp = row.get("qty"), row.get("avg"), row.get("ltp")
    if row.get("value") is None and ltp is not None and qty is not None:
        row["value"] = ltp * qty
    cost = avg * qty if (avg is not None and qty is not None) else None
    if row.get("pnl") is None and row.get("value") is not None and cost is not None:
        row["pnl"] = row["value"] - cost
    if row.get("pnl_pct") is None and row.get("pnl") is not None and cost:
        row["pnl_pct"] = row["pnl"] / cost * 100
    return row


def last4(s):
    s = str(s or "")
    return f"A/C ··{s[-4:]}" if len(s) >= 4 else "account"
