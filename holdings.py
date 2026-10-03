"""Holdings: every source the desk can see the reader's positions in, any market.

Desk · Book, the broker's last snapshot, and a positions file the reader brings
in on Settings all answer the same two questions: which names does the reader
hold or watch in a market, and where did each name come from. A screen asks the
desk's `universe()` instead of reading the book and a watch grid itself, so a
source added once reaches every screen that works off the reader's own names.

A name's market comes from its suffix through `markets/`: BHP.AX is Australia,
SHEL.L the United Kingdom, RELIANCE.NS India, and a symbol with no suffix is the
United States, which is how Yahoo writes them. So a reader in Sydney or Frankfurt
brings in the positions they actually hold and the desk files each one under its
own market, with that market's currency and its own index behind it.

Nothing here reaches a network and nothing here places an order. A file the
reader brings in is read once into the desk's own folder and never written back.
"""

import csv
import io
import json
import math
import os
import re
import threading
import time

import markets
from markets import world

# Yahoo writes a US listing with no suffix, so a bare symbol is a US name. Everything
# else is decided by the suffix, from the one table the market layer already keeps.
US = "us"
SYMBOL_OK = re.compile(r"^[A-Z][A-Z0-9.\-]{0,15}$")

_lock = threading.Lock()
_suffixes = {"map": None}
_cache = {"rows": None, "at": 0.0, "folder": ""}


def _suffix_map():
    """{".AX": "au", ".L": "gb", ...} from the market layer, built once."""
    with _lock:
        if _suffixes["map"] is None:
            out = {}
            for rid, row in getattr(world, "EXCHANGES", {}).items():
                for _name, suf in (row[2] or []):
                    if suf:
                        out.setdefault(suf.upper(), rid)
            # the markets with a file of their own name their suffixes through ysym
            for rid in getattr(markets, "FILES", []):
                m = markets.load(rid)
                for exch in (m.META.get("exchanges") or []):
                    suf = m.ysym("X", exch)[1:]
                    if suf:
                        out.setdefault(suf.upper(), rid)
            _suffixes["map"] = out
        return _suffixes["map"]


def market_of(symbol):
    """The market a Yahoo symbol belongs to; a symbol with no suffix is US."""
    s = str(symbol or "").upper().strip()
    if not s:
        return ""
    if "." in s:
        suf = s[s.rfind("."):]
        return _suffix_map().get(suf, "")
    return US


def in_market(symbol, market):
    """True when this symbol trades in this market."""
    return bool(symbol) and market_of(symbol) == (market or "").lower()


def market_label(market):
    """The market's name in plain words, for a line the reader reads."""
    m = markets.load(market)
    return (m.META.get("label") if m else "") or (market or "").upper()


# ---- positions the reader brings in on Settings ------------------------------
# One file per import, kept in the reader's own data folder as the desk's own JSON,
# so the original stays wherever the reader keeps it. Each import is its own book:
# it sits beside Desk · Book and the broker's accounts on Risk and never replaces them.

FORMAT = 1
# old format -> fn(dict) -> dict, one step each; registered in migrate.py KINDS so a reader's
# older file is carried forward rather than read by code that no longer understands it
MIGRATIONS = {}
COLUMNS = {
    "symbol": ("symbol", "ticker", "instrument", "instrument_id", "code", "security", "stock", "name"),
    "shares": ("shares", "quantity", "qty", "units", "position", "holding", "no of shares",
               "share", "nos", "quantity available", "available quantity"),
    # the price paid for one share; "price" alone is today's price on most exports, so it is not here
    "avg_cost": ("avg_cost", "avg cost", "average cost", "avg price", "average price", "avg",
                 "cost", "cost basis", "book cost", "buy price", "avg. cost",
                 "average", "avg buy price", "purchase price", "unit cost", "average cost basis",
                 "avg cost basis", "cost per share", "cost/share", "average cost per share",
                 "avg cost/share", "average purchase price"),
    # what the whole position cost; divided by the shares when no per-share column is there
    "cost_total": ("cost basis total", "total cost", "total cost basis", "total book cost",
                   "invested", "invested amount", "amount invested"),
    # today's price, read only to tell a total from a per-share cost when the column name could be either
    "last_price": ("price", "last price", "current price", "ltp", "last", "market price",
                   "share price", "close price", "last traded price"),
    "currency": ("currency", "ccy", "curr"),
    "account": ("account", "account_id", "account name", "portfolio", "folio"),
    "exchange": ("exchange", "exch", "market", "listing"),
}

# Column names that mean the price of one share on one broker and the whole position's cost
# on another: Schwab's Cost Basis and a UK broker's Book cost are totals, a German export's
# Cost basis is per share. Today's price on the same row settles which it is.
_EITHER = ("cost", "cost basis", "book cost")


def _dir(data_dir):
    return os.path.join(data_dir, "holdings")


def _num(v):
    """A number the way the reader's own country writes it.

    An export from Frankfurt writes one hundred and ninety eight euros fifty as
    198,50 and a thousand as 1.105,50; London and New York write them the other
    way round. Reading 198,50 as 19850 would put a cost base out by a hundred
    times, so the separators are decided per value: the last one to appear, with
    two or fewer digits behind it and no separator after it, is the decimal.
    """
    s = re.sub(r"[^\d,.\-()]", "", str(v or "").strip())
    if not s:
        return None
    neg = s.startswith("-") or (s.startswith("(") and s.endswith(")"))   # (1,234) is negative
    s = s.strip("()-")
    dot, comma = s.rfind("."), s.rfind(",")
    if dot >= 0 and comma >= 0:
        # both appear: the later one is the decimal point, the earlier groups thousands
        dec, grp = (".", ",") if dot > comma else (",", ".")
        s = s.replace(grp, "").replace(dec, ".")
    elif comma >= 0:
        # one comma only: a decimal when one or two digits follow it (198,5 · 198,50),
        # a thousands separator otherwise (1,105 · 1,105,500)
        s = s.replace(",", "." if len(s) - comma - 1 in (1, 2) else "")
    try:
        n = float(s)
    except ValueError:
        return None
    return -n if neg else n


def _safe_name(name):
    base = re.sub(r"[^a-z0-9_-]+", "-", str(name or "").lower()).strip("-")[:40]
    return base or "positions"


def _column_index(header):
    """Which column holds what, from whatever the export called it.

    A name in brackets after the column's own name is dropped, so Schwab's
    "Qty (Quantity)" is read as qty.
    """
    found, names = {}, {}
    for i, cell in enumerate(header):
        key = str(cell or "").strip().lower().replace("_", " ")
        short = re.sub(r"\s*\(.*?\)\s*", " ", key).strip()
        for field, aliases in COLUMNS.items():
            if field in found:
                continue
            for k in (key, short):
                if k in aliases or k.replace(" ", "_") in aliases:
                    found[field] = i
                    names[field] = k
                    break
    found["_names"] = names
    return found


def _per_share(cost, shares, price, either):
    """The price paid for one share, from a column that may hold the whole position's cost."""
    if not cost or not shares or not either or not price or price <= 0:
        return cost
    # whichever reading lands nearer today's price is the one the export meant
    as_is = abs(math.log(abs(cost) / price))
    divided = abs(math.log(abs(cost / shares) / price))
    return cost / shares if divided < as_is else cost


def _with_suffix(symbol, exchange, market=""):
    """Turn the code the reader's own broker printed into the symbol Yahoo knows.

    A broker in Sydney exports BHP and one in Mumbai exports RELIANCE, because a
    local broker has no reason to name the market its own reader is standing in.
    The row's exchange decides it when the export named one; otherwise the market
    the reader picked for the file does. Nothing is guessed: with neither, the
    symbol stays as it came and `parse` files it under the US, which is how Yahoo
    writes a US listing, and says so in the file's notes.
    """
    s = str(symbol or "").upper().strip()
    if not s or "." in s:
        return s
    want = str(exchange or "").strip().upper()
    if want:
        for rid in markets.REGISTRY:
            m = markets.load(rid)
            for exch in ((m.META.get("exchanges") or []) if m else []):
                if exch.upper() == want:
                    return m.ysym(s, exch)
    if market and market != US:
        m = markets.load(market)
        if m:
            return m.ysym(s)
    return s


# a currency that belongs to exactly one market on the desk; EUR and USD are shared,
# so they say nothing about where a file came from and are left out on purpose
_ONE_MARKET_CCY = {}


def currency_market(currency):
    """The market a currency belongs to, when it belongs to only one."""
    cur = str(currency or "").upper().strip()
    if not cur:
        return ""
    with _lock:
        if not _ONE_MARKET_CCY:
            seen = {}
            for rid in markets.REGISTRY:
                m = markets.load(rid)
                # only a market with an exchange can be where a share was bought: Kiribati
                # and Nauru spend Australian dollars and list nothing, so they would make
                # the one currency that does name a market look ambiguous
                if not m or not (m.META.get("exchanges") or []):
                    continue
                c = (m.META.get("currency") or "").upper()
                if c:
                    seen.setdefault(c, []).append(rid)
            _ONE_MARKET_CCY.update({c: ids[0] for c, ids in seen.items() if len(ids) == 1})
    return _ONE_MARKET_CCY.get(cur, "")


def parse(text, filename="", market=""):
    """Read a positions file the reader brings in: their export, their column names.

    Takes a CSV from a broker or a spreadsheet, or JSON in the desk's own book
    shape. `market` is the market the reader says the file came from, which is
    what gives a bare local code its suffix: BHP from a Sydney export becomes
    BHP.AX. Returns the positions it understood and a plain-words line for each
    row it could not, so nothing is dropped in silence.
    """
    rows, skipped, notes = [], [], []
    market = (market or "").lower().strip()
    raw = text.lstrip("﻿") if isinstance(text, str) else text.decode("utf-8", "replace").lstrip("﻿")
    body = raw.strip()

    if body.startswith("{") or body.startswith("["):
        try:
            data = json.loads(body)
        except ValueError as exc:
            return {"positions": [], "skipped": [f"the file is not readable JSON ({exc.msg})"], "label": ""}
        items = data if isinstance(data, list) else (data.get("positions") or data.get("holdings") or [])
        for i, p in enumerate(items, 1):
            if not isinstance(p, dict):
                skipped.append(f"line {i}: not a position")
                continue
            sym = ""
            for k in COLUMNS["symbol"]:
                if p.get(k):
                    sym = str(p[k]).upper().strip()
                    break
            exch = next((str(p[k]) for k in COLUMNS["exchange"] if p.get(k)), "")
            sym = _with_suffix(sym, exch, market)
            shares = next((_num(p[k]) for k in COLUMNS["shares"] if p.get(k) is not None), None)
            avg = next((_num(p[k]) for k in COLUMNS["avg_cost"] if p.get(k) is not None), None)
            rows.append({"symbol": sym, "shares": shares, "avg_cost": avg,
                         "currency": next((str(p[k]).upper() for k in COLUMNS["currency"] if p.get(k)), ""),
                         "account": next((str(p[k]) for k in COLUMNS["account"] if p.get(k)), "")})
    else:
        try:
            table = list(csv.reader(io.StringIO(body), delimiter=_delimiter(body)))
        except csv.Error as exc:
            return {"positions": [], "skipped": [f"the file could not be read as a table ({exc})"], "label": ""}
        table = [r for r in table if any(str(c).strip() for c in r)]
        if not table:
            return {"positions": [], "skipped": ["the file has no rows"], "label": ""}
        # a broker export often carries a title line or two before the real header
        idx, header_at = {}, -1
        for i, row in enumerate(table[:10]):
            got = _column_index(row)
            if "symbol" in got:
                idx, header_at = got, i
                break
        if header_at < 0:
            return {"positions": [], "skipped": ["no column names a symbol or ticker; "
                                                 "the first row should name its columns"], "label": ""}
        for n, row in enumerate(table[header_at + 1:], header_at + 2):
            def cell(field):
                i = idx.get(field)
                return row[i] if i is not None and i < len(row) else ""
            sym = str(cell("symbol")).upper().strip()
            if not sym:
                continue
            sym = _with_suffix(sym, cell("exchange"), market)
            shares = _num(cell("shares"))
            avg = _num(cell("avg_cost"))
            if avg is None and shares and _num(cell("cost_total")):
                avg = _num(cell("cost_total")) / shares
            elif avg is not None:
                avg = _per_share(avg, shares, _num(cell("last_price")),
                                 idx["_names"].get("avg_cost") in _EITHER)
            rows.append({"symbol": sym, "shares": shares, "avg_cost": avg,
                         "currency": str(cell("currency")).upper().strip(),
                         "account": str(cell("account")).strip(), "_line": n})

    out = []
    for p in rows:
        sym, line = p["symbol"], p.pop("_line", None)
        where = f"line {line}: " if line else ""
        if not SYMBOL_OK.match(sym):
            skipped.append(f"{where}\"{sym[:24]}\" is not a symbol the desk can price")
            continue
        if not p["shares"]:
            skipped.append(f"{where}{sym} has no number of shares")
            continue
        mkt = market_of(sym)
        if not mkt:
            skipped.append(f"{where}{sym} ends in a suffix no market on the desk uses")
            continue
        out.append({"symbol": sym, "market": mkt, "shares": p["shares"],
                    "avg_cost": p["avg_cost"] or 0.0,
                    "currency": p["currency"] or (markets.load(mkt).META.get("currency") if markets.load(mkt) else ""),
                    "account": p["account"]})

    # A local broker prints the local code, so a file read as US names when its own
    # money is not dollars is the one mistake that would go unnoticed: every screen
    # would still fill, with the wrong companies. The reader is told, and told which
    # market to pick, rather than the desk deciding for them.
    bare = [p for p in out if p["market"] == US and "." not in p["symbol"]]
    if bare and not market:
        other = {p["currency"] for p in bare if p["currency"] and p["currency"] != "USD"}
        if other:
            n = len(bare)
            one = n == 1
            suggest = next((currency_market(c) for c in sorted(other) if currency_market(c)), "")
            tail = (f"Bring the file in again against {market_label(suggest)} if that is where "
                    + ("it trades." if one else "they trade.")) if suggest else \
                   ("Bring the file in again against the market it trades in." if one else
                    "Bring the file in again against the market they trade in.")
            notes.append(
                ("One name carries no market in the file and is priced in " if one else
                 f"{n} names carry no market in the file and are priced in ")
                + f"{' and '.join(sorted(other))}, not dollars, so the desk has read "
                + ("it as a US listing. " if one else "them as US listings. ") + tail)

    counted = {}
    for p in out:
        counted[p["market"]] = counted.get(p["market"], 0) + 1
    label = re.sub(r"\.(csv|json|txt|tsv)$", "", os.path.basename(filename or ""), flags=re.I) or "Positions"
    return {"positions": out, "skipped": skipped, "notes": notes, "label": label[:40],
            "markets": [{"market": k, "label": market_label(k), "names": v}
                        for k, v in sorted(counted.items(), key=lambda kv: -kv[1])]}


def _delimiter(body):
    head = body.split("\n", 1)[0]
    return max((",", ";", "\t"), key=head.count)


def save(data_dir, parsed, label=""):
    """Keep an import as the desk's own file; returns the row the screens read."""
    folder = _dir(data_dir)
    os.makedirs(folder, exist_ok=True)
    name = _safe_name(label or parsed.get("label"))
    row = {"_comment": "Positions brought in on Settings. The desk reads this file and never "
                       "writes your original. Delete it here or on Settings to drop these names.",
           "format": FORMAT, "label": (label or parsed.get("label") or "Positions")[:40],
           "brought_in": time.strftime("%Y-%m-%d %H:%M"), "positions": parsed["positions"]}
    path = os.path.join(folder, name + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(row, fh, indent=2)
    _cache["rows"] = None
    return row | {"name": name, "path": path}


def imported(data_dir, force=False):
    """Every positions file the reader has brought in, by label.

    Read at most once every few seconds, and remembered against the folder it was
    read from: a desk has one data folder, but the answer for one folder must never
    be served for another.
    """
    folder = _dir(data_dir)
    with _lock:
        if (not force and _cache["rows"] is not None and _cache.get("folder") == folder
                and time.time() - _cache["at"] < 5):
            return list(_cache["rows"])
    rows = []
    if os.path.isdir(folder):
        for fn in sorted(os.listdir(folder)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(folder, fn), encoding="utf-8") as fh:
                    row = json.load(fh)
            except (OSError, ValueError):
                rows.append({"name": fn[:-5], "label": fn[:-5], "positions": [],
                             "error": "this file could not be read"})
                continue
            good = [p for p in (row.get("positions") or [])
                    if isinstance(p, dict) and SYMBOL_OK.match(str(p.get("symbol") or "").upper())
                    and _num(p.get("shares"))]
            for p in good:
                p["symbol"] = str(p["symbol"]).upper()
                p.setdefault("market", market_of(p["symbol"]))
            rows.append({"name": fn[:-5], "label": str(row.get("label") or fn[:-5])[:40],
                         "brought_in": str(row.get("brought_in") or ""), "positions": good})
    with _lock:
        _cache["rows"], _cache["at"], _cache["folder"] = rows, time.time(), folder
    return list(rows)


def remove(data_dir, name):
    """Drop one import. The reader's own original file is untouched."""
    safe = _safe_name(name)
    path = os.path.join(_dir(data_dir), safe + ".json")
    if not os.path.isfile(path):
        return False
    os.remove(path)
    _cache["rows"] = None
    return True


def positions(data_dir, market=None):
    """Every imported position, in one market or all of them."""
    out = []
    for row in imported(data_dir):
        for p in row["positions"]:
            if market and p.get("market") != market:
                continue
            out.append(p | {"source": row["label"]})
    return out
