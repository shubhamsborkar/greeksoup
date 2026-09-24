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
import threading
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Alphabetical by label. Adding a broker = one file here + one line in this list.
REGISTRY = ["alpaca", "angel_one", "schwab", "dhan", "groww", "icici_breeze", "ibkr_flex",
            "longbridge", "questrade", "saxo", "tastytrade", "tradier", "trading212",
            "upstox", "zerodha_kite"]

# Brokers the desk knows about but does not ship a file for, and the honest path
# for each. Shown on the Settings screen under "Another broker".
OTHERS = [
    # Checked 2026-09-17 against each broker's own developer page, the Indian rows 2026-09-22
    # and the rest of the world 2026-09-23; a price is the broker's, and can change.
    ("Fyers, 5paisa", "Each has a free API with a daily login, the same pattern as the Indian brokers shipped here; the same market file serves all of them. Your agent writes it from their documentation."),
    ("Kotak Neo, HDFC Securities (InvestRight)", "Free APIs for their own clients; keys from developer portals (developer.hdfcsec.com for HDFC). Your agent writes the file the same way."),
    ("Zerodha", "Shipped here. The personal API is free for holdings, positions and funds; live and historical data through it is ₹500 a month, and the desk prices the book from the free feed without it."),
    ("Groww", "Shipped here. The trading API is a paid subscription, and Groww asks you to approve the key on its keys page each day."),
    ("Public, Webull, moomoo", "Each has an official API for its own clients; Webull asks individuals to apply and approves in a day or two, and moomoo goes through its OpenD gateway on this computer. Your agent writes the file from their documentation."),
    ("Tiger Brokers", "An official API across Singapore, Australia, New Zealand and Hong Kong. Its requests are signed with a key pair rather than a secret, so the file needs one more library than the desk ships."),
    ("E*TRADE", "An API exists, with an approval process and a balance minimum. Export the holdings into Desk · Book unless you already have access."),
    ("Fidelity, Vanguard", "No API for individuals. Export the holdings to a file and paste them into Desk · Book; most exports paste straight in."),
    ("Robinhood", "No API for stocks (only for crypto). Export the holdings into Desk · Book, or have your agent connect Robinhood's own agent server."),
    ("Nordnet", "The Nordic one with an API, but it is closed to new applicants. If you already have access, your agent writes the file from nordnet.se/externalapi/docs."),
    ("XTB", "It withdrew the API on 14 March 2025 and has not replaced it; the broker now points clients at its own platform. Export the holdings into Desk · Book."),
    ("Trade Republic, Scalable Capital, DEGIRO, Revolut, eToro", "No API for individuals, whatever a third-party library claims. Export the holdings into Desk · Book."),
    ("Brazil and the rest of South America", "No broker there publishes a self-serve API for individuals. Access to the exchange goes through a vendor your broker has to authorise for you, account by account. Interactive Brokers, shipped here, is the way in that does not need one; otherwise Desk · Book takes an export."),
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


def active_ids():
    """The brokers the reader connected, in order: BROKERS=zerodha_kite,alpaca in .env (one per
    market; the first is the home one), else the single BROKER line, else, for a copy set up
    before the picker existed, the first configured file."""
    raw = (os.getenv("BROKERS", "") or "").strip().lower()
    ids = [b.strip() for b in raw.split(",") if b.strip() in REGISTRY]
    if ids:
        return ids
    bid = (os.getenv("BROKER", "") or "").strip().lower()
    if bid in REGISTRY:
        return [bid]
    if bid in ("", "none"):
        for cand in REGISTRY:
            if configured(cand):
                return [cand]
    return []


def active_id():
    """The home broker: the first of the connected ones."""
    ids = active_ids()
    return ids[0] if ids else ""


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
# One file per broker, session_token_<broker>.txt, a date line then the token; gitignored.
# The home broker also reads the older session_token_primary.txt, so a copy that logged in
# before brokers had files of their own keeps its session.
# Most brokers' regulators want the login repeated every trading day, which is the default.
# A broker whose session lasts longer says so with META["login_days"]; Schwab's is seven.
TOKEN_PATH = os.path.join(ROOT, "session_token_primary.txt")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def login_days(broker_id=None):
    m = load(broker_id or active_id())
    try:
        return max(1, int((m.META.get("login_days") if m else 1) or 1))
    except (TypeError, ValueError):
        return 1


def token_path(broker_id=None):
    bid = (broker_id or active_id() or "").strip().lower()
    return os.path.join(ROOT, f"session_token_{bid}.txt") if bid else TOKEN_PATH


def _read_token_file(path, days=1):
    try:
        with open(path, encoding="utf-8") as fh:
            date_line = fh.readline().strip()
            token = fh.readline().strip()
    except OSError:
        return None
    if not token:
        return None
    if days <= 1:
        return token if date_line == _today() else None
    try:
        made = datetime.strptime(date_line, "%Y-%m-%d").date()
    except ValueError:
        return None
    age = (datetime.now().date() - made).days
    return token if 0 <= age < days else None


def read_token(broker_id=None):
    bid = broker_id or active_id()
    days = login_days(bid)
    tok = _read_token_file(token_path(bid), days)
    if tok is None and bid == active_id():
        tok = _read_token_file(TOKEN_PATH, days)
    return tok


def write_token(token, broker_id=None):
    with open(token_path(broker_id), "w", encoding="utf-8") as fh:
        fh.write(f"{_today()}\n{token}\n")


def clear_token(broker_id=None):
    for path in {token_path(broker_id), TOKEN_PATH} if (broker_id or active_id()) == active_id() else {token_path(broker_id)}:
        try:
            os.remove(path)
        except OSError:
            pass


# ---- helpers shared by the adapters ------------------------------------------
def quote_row(code, exch, ltp, prev=None, o=None, h=None, l=None, depth=None, volume=None):
    """A live price in the watch-grid shape every broker's quote() returns. depth is the
    broker's {"buy": [{"price", "quantity"}], "sell": [...]}; its first level fills the
    bid and the offer."""
    ltp, prev = num(ltp), num(prev)
    if not ltp:
        return None
    book = depth if isinstance(depth, dict) else {}
    buy = (book.get("buy") or [{}])[0] or {}
    sell = (book.get("sell") or [{}])[0] or {}
    return {
        "code": code, "exch": exch, "ltp": ltp, "prev": prev,
        "day_pct": (ltp - prev) / prev * 100 if prev else None,
        "bid": num(buy.get("price")) or None, "bid_qty": num(buy.get("quantity")),
        "offer": num(sell.get("price")) or None, "offer_qty": num(sell.get("quantity")),
        "open": num(o), "high": num(h), "low": num(l), "ttq": num(volume),
        "ts": time.strftime("%H:%M:%S"),
    }


def quotes_refused(client):
    """The broker said no to prices on this account (no market-data plan): the desk stops
    asking for the rest of the session and prices the names from the free feed."""
    if isinstance(client, dict):
        client["quotes_off"] = True
    return None


MISS_LIMIT = 8


def quote_result(client, row):
    """Count the answers: a broker that has priced nothing for MISS_LIMIT names in a row,
    on a session that is otherwise alive, is treated as having said no, whatever words it
    used. One good price resets the count."""
    if isinstance(client, dict):
        if row:
            client["quote_misses"] = 0
        else:
            client["quote_misses"] = client.get("quote_misses", 0) + 1
            if client["quote_misses"] >= MISS_LIMIT:
                client["quotes_off"] = True
    return row


def quotes_off(client):
    return isinstance(client, dict) and bool(client.get("quotes_off"))


_paced = {}
_pace_lock = threading.Lock()


def pace(key, gap):
    """Keep calls under a broker's stated rate: at least gap seconds between two."""
    with _pace_lock:
        wait = _paced.get(key, 0) + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _paced[key] = time.time()


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


def totp_now(secret, broker="This broker", digits=6, period=30):
    """The six digits an authenticator app would be showing right now.

    Several brokers make a code from an authenticator app part of the sign-in. The
    reader saves the secret behind that QR code once, in .env with the rest of the
    broker's keys, and the desk works the digits out here (RFC 6238) rather than
    asking for them every morning. No key leaves this computer.
    """
    import base64
    import hashlib
    import hmac
    import struct
    import time

    key = "".join((secret or "").split()).upper()
    try:
        raw = base64.b32decode(key + "=" * (-len(key) % 8), casefold=True)
    except (ValueError, TypeError) as exc:
        raise BrokerError(f"{broker}'s authenticator secret is not readable. It is the "
                          "letters shown beside the QR code when you turned it on, not the six digits.") from exc
    if not raw:
        raise BrokerError(f"{broker} needs the authenticator secret before it can sign in.")
    mac = hmac.new(raw, struct.pack(">Q", int(time.time()) // period), hashlib.sha1).digest()
    off = mac[-1] & 0x0F
    code = (struct.unpack(">I", mac[off:off + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)
