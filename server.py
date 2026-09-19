"""The desk's server. READ-ONLY: there is no order code path.

    python server.py
    open http://localhost:8765

Serves the pages under web/ and the JSON they poll (the list is on /agent).
The broker the reader chose on Settings is read through one file in brokers/;
the market that broker trades in is served by one file in markets/. Nothing
in this file assumes a particular broker, market or data provider.
"""

import json
import os
import sys

# A Python installed from python.org ships without a certificate store, so every https call
# made through the standard library (a broker's SDK, urllib) fails with "certificate verify
# failed". The bundle requests carries stands in for the whole process, set before any
# library that opens a connection is imported.
try:
    import certifi as _certifi
    os.environ.setdefault("SSL_CERT_FILE", _certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _certifi.where())
except ImportError:
    pass
import subprocess
import shutil
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv

# .env is read once here, so DESK_PORT and DESK_AUTO_UPDATE in it take effect
# for the desk itself, not only for the broker adapter.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import activist
import commods
import insiders
import options_us
import risk
import shortint
import updater          # the daily version check and the one-click update
import settings as desk_settings   # the Settings screen: keys, token, switches
import ai as desk_ai               # the reader's own AI key, tested here
import brokers                     # the broker layer: one file per broker, read-only
import markets                     # the market layer: one file per home market
import fred                        # FRED, keyless
import freefeed          # keyless Yahoo fallbacks for the US pages
import sec_form4         # keyless Form 4 from EDGAR
import house_ptr         # keyless House trading disclosures
import notes as desk_notes   # the research vault: notes and files in data/research, linked to names and projects
import plugins as desk_plugins   # folders in data/research/plugins that add a screen, blocks or a door
import chains as desk_chains     # the reader's own value chains in data/research/chains, starters beside the code
import migrate as desk_migrate   # reader-owned files carry a format number; an update brings them up, a copy kept aside
import lists as desk_lists
import calendar_desk                 # the Calendar: results, dividends, filings on every name held or watched, from the free record       # the reader's own lists (funds, members, macro series, commodities, the tape) in the vault, starters beside the code

PORT = int(os.getenv("DESK_PORT", "8765"))
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")   # the files you edit: watchlists, book, funds, alerts

SNAP_TTL = 30      # seconds between fresh broker pulls for positions/funds
TAPE_TTL = 600     # option chains are heavy; refresh every 10 min

clients = {}          # broker id -> its connected client
MODS = {}             # broker id -> its module, for every broker the reader connected
ACCOUNT_LABELS = {}   # account key -> "A/C ··1234" (last four digits, never a name)
# The brokers the reader connected on Settings, one per market: each is an account on
# Desk · Home, in its own desk (the home market's, the US, the rest of the world), never
# added together. ADAPTER is the home broker (the one whose market is the home market, else
# the first): its optional hooks (live ticks, futures, margin, chains, candles, a symbol
# master) serve the home screens; _hook() finds them or returns None.
ADAPTER = {"id": "", "mod": None}


def _mod_of(account):
    """The module behind an account key (a broker id), the home adapter for anything older."""
    return MODS.get(account) or ADAPTER["mod"]


def _client():
    """The home broker's client, and only that one: a hook in the home broker's file must never
    be handed another desk's client (Alpaca's, while ICICI waits for its login)."""
    return clients.get(ADAPTER["id"])


def _hook(name, live=True):
    """The home broker file's optional function `name`, if it has one. Most
    hooks need a connected client; the symbol master (resolve, search) does
    not, so those pass live=False and work with the session down."""
    mod = ADAPTER["mod"]
    if mod is None or (live and not _client()):
        return None
    return getattr(mod, name, None)


def _market():
    """The home market file: the reader's own choice (HOME_MARKET in .env) first, else the
    home broker's market. A reader with a US broker and a home in India keeps India."""
    chosen = (os.getenv("HOME_MARKET", "") or "").strip()
    if chosen and markets.load(chosen):
        return markets.load(chosen)
    mod = ADAPTER["mod"]
    return markets.active(mod.META.get("region") if mod else None)


def _home_id():
    m = _market()
    return str(m.META.get("id", "")).lower() if m else ""


desk_chains.home_id = _home_id      # a chain's country resolves to its quote path against the desk's home


def _pick_adapter():
    """The home broker among the connected ones: the one in the home market, else the first."""
    ids = brokers.active_ids()
    chosen = (os.getenv("HOME_MARKET", "") or "").strip().lower()
    home = next((b for b in ids if MODS.get(b) and str(MODS[b].META.get("region", "")).lower() == chosen), None) if chosen else None
    bid = home or (ids[0] if ids else "")
    ADAPTER["id"], ADAPTER["mod"] = bid, MODS.get(bid)


def desk_of(region):
    """Which desk an account sits on, by its broker's market: the home market's, the US, or the rest."""
    r = str(region or "").lower()
    m = _market()
    home = str(m.META.get("id", "")).lower() if m else ""
    if r and r == home:
        return "home"
    if r == "us":
        return "us"
    return "global"


# A daily-login broker's session ends at midnight. When every pull comes back
# empty the pages show a "log in again" notice instead of misleading zeros.
broker_health = {"dead": not clients}
_cache = {"snap": (0.0, None), "tape": (0.0, None),
          "earn": (0.0, None), "results_home": (0.0, None), "macro": (0.0, None),
          "funds": (0.0, None), "capitol": (0.0, None), "econcal": (0.0, None),
          "pulse": (0.0, None), "insiders": (0.0, None),
          "risk": (0.0, None), "act13d": (0.0, None), "flow": (0.0, None),
          "short": (0.0, None), "commods": (0.0, None), "chain": (0.0, None),
          "book": (0.0, None), "calendar": (0.0, None)}
_locks = {k: threading.Lock() for k in _cache}
EARN_TTL, MACRO_TTL, FUNDS_TTL, CAPITOL_TTL = 12 * 3600, 6 * 3600, 24 * 3600, 6 * 3600
COMMODS_TTL = 10 * 60   # Yahoo tail + TE sentence refresh; histories cache 12h inside


# ---- watchlist ---------------------------------------------------------------
WATCHLIST_PATH = os.path.join(DATA_DIR, "watchlist.json")
WATCH = {}                     # code -> latest quote dict
_watch_lock = threading.Lock()


def _num(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, "", "NA"):
            return d[k]
    return None


def load_watchlist():
    with open(WATCHLIST_PATH) as fh:
        return json.load(fh).get("names", [])


def save_watchlist(names):
    with open(WATCHLIST_PATH, "w") as fh:
        json.dump({"_comment": "Edit in the Watchlist page.", "format": 1, "names": names}, fh, indent=2)


def _is_broker_name(entry):
    """A home watch name quoted through the broker (older lists say "breeze")."""
    return entry.get("source", "broker") in ("broker", "breeze")


def _resolve(code, exch=None):
    """What the desk knows about a home code: the exchange symbol, the exchange,
    a name and Yahoo's symbol. Through the broker's symbol master when it has
    one, else the code is the exchange symbol and the market file spells Yahoo's."""
    hook = _hook("resolve", live=False)
    if hook:
        try:
            r = hook(code)
        except Exception:  # noqa: BLE001
            r = None
        if r:
            return r
    m = _market()
    # a name added by company name carries the free feed's symbol (HDFCBANK.NS): the exchange
    # symbol and the exchange come out of it, so the exchange's own record (results, filings,
    # shareholding) is read for HDFCBANK, which the exchange knows, and not HDFCBANK.NS
    split = m.from_ysym(code) if (m and hasattr(m, "from_ysym") and "." in code) else None
    if split:
        return {"symbol": split[0], "exch": split[1], "name": "", "ysym": code.upper(), "meta": {}}
    exch = exch or (m.META["exchanges"][0] if m else "")
    ysym = m.ysym(code, exch) if m else code
    return {"symbol": code, "exch": exch, "name": "", "ysym": ysym, "meta": {}}


def _home_quote(code, exch=None, tries=1):
    """One quote for a home name: the broker's own when its file serves quotes
    (with the order book), else Yahoo through the resolved symbol."""
    hook = _hook("quote")
    cli = _client()
    # a name the reader added by company name carries the free feed's own symbol
    # (HDFCBANK.NS, SHEL.L): the broker is asked through its own code for that symbol
    # when its master knows one (HDFCBANK on the NSE is HDFBAN at ICICI), so the session
    # and the order book come from the broker for that name too; SHEL.L has no such code
    # and the free feed prices it
    ask = code
    if "." in code:
        m = _market()
        split = m.from_ysym(code) if (m and hasattr(m, "from_ysym")) else None
        back = _hook("code_of", live=False)
        ask = (back(split[0], split[1]) if (split and back) else None) or ""
        if ask and not exch:
            exch = split[1]
    if hook and cli and not broker_health["dead"] and ask:
        m = _market()
        exchanges = [exch] if exch else []
        exchanges += [e for e in (m.META["exchanges"] if m else []) if e not in exchanges]
        for attempt in range(max(1, tries)):
            for ex in exchanges or [None]:
                q = hook(cli, ask, ex) if ex else hook(cli, ask)
                if q:
                    q["code"] = code
                    return q
            if attempt + 1 < tries:
                time.sleep(0.8)
        # the broker had nothing for this code (a lapsed session, a code its quote
        # feed does not serve): the free feed through the resolved symbol, the same
        # way the candles already fall back, rather than a page with no quote
    r = _resolve(code, exch)
    q = fetch_yahoo_quote(r["ysym"]) if r.get("ysym") else None
    if q:
        q["code"] = code
        q["exch"] = q.get("exch") or r.get("exch") or ""
    return q


# ---- US watchlist (FMP) ------------------------------------------------------
WATCHLIST_US_PATH = os.path.join(DATA_DIR, "watchlist_us.json")
US_WATCH_STARTERS = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "COST", "LLY", "XOM"}   # the names Watch · US ships with
WATCH_US = {}
_fmp_backoff = {"until": 0.0}


def us_market_open(now=None):
    """US regular session in UTC (13:30-20:00 covers EDT; close enough for a
    status dot — the data itself is whatever FMP serves)."""
    now = now or datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return False
    hm = now.hour * 60 + now.minute
    return (13 * 60 + 30) <= hm < (20 * 60)


def load_watchlist_us():
    with open(WATCHLIST_US_PATH) as fh:
        return json.load(fh).get("names", [])


def save_watchlist_us(names):
    with open(WATCHLIST_US_PATH, "w") as fh:
        json.dump({"_comment": "Edit in the Watch US page.", "format": 1, "names": names}, fh, indent=2)


def fetch_us_quote(symbol):
    """One FMP quote, normalized to the watch-grid schema. None if nothing."""
    key = os.getenv("FMP_API_KEY", "").strip()
    if not key or time.time() < _fmp_backoff["until"]:
        return None
    try:
        r = requests.get(
            "https://financialmodelingprep.com/stable/quote",
            params={"symbol": symbol, "apikey": key}, timeout=10)
        if r.status_code == 429:          # rate-limited: back off 5 min
            _fmp_backoff["until"] = time.time() + 300
            return None
        rows = r.json()
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(rows, list) or not rows:
        return None
    q = rows[0]
    price = _num(q.get("price"))
    if price is None or price <= 0:
        return None
    d50, d200 = _num(q.get("priceAvg50")), _num(q.get("priceAvg200"))
    return {
        "code": symbol, "exch": q.get("exchange") or "US", "name": q.get("name"),
        "ltp": price, "prev": _num(q.get("previousClose")),
        "day_pct": _num(q.get("changePercentage")), "chg": _num(q.get("change")),
        "open": _num(q.get("open")), "high": _num(q.get("dayHigh")),
        "low": _num(q.get("dayLow")), "ttq": _num(q.get("volume")),
        "yhigh": _num(q.get("yearHigh")), "ylow": _num(q.get("yearLow")),
        "vs50": ((price - d50) / d50 * 100) if d50 else None,
        "vs200": ((price - d200) / d200 * 100) if d200 else None,
        "mcap": _num(q.get("marketCap")),
        "ts": datetime.now().strftime("%H:%M:%S"),
    }


# ---- Yahoo batch quotes (the "live" Watch·US path) ---------------------------
# One request quotes the whole list, so a ten-second cadence is polite. Needs a
# session cookie + crumb; when Yahoo throttles the crumb, we fall back to a
# parallel FMP sweep (10s full-grid refresh) until the next crumb attempt.
_yahoo = {"session": None, "crumb": None, "next_try": 0.0}
def _yahoo_auth():
    if time.time() < _yahoo["next_try"]:
        return False
    try:
        s = requests.Session()
        s.headers.update(freefeed.UAS[freefeed._ua["i"]])   # the browser string Yahoo last answered
        s.get("https://fc.yahoo.com", timeout=10)
        crumb = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb",
                      timeout=10).text.strip()
        if crumb and "Too Many" not in crumb and len(crumb) <= 16:
            _yahoo.update(session=s, crumb=crumb)
            print("  Yahoo batch quotes: ON (crumb ok); Watch·US refreshes every ~10s in-session")
            return True
    except Exception:  # noqa: BLE001
        pass
    _yahoo.update(session=None, crumb=None, next_try=time.time() + 600)
    return False


def fetch_us_batch(symbols):
    """All US names in ONE Yahoo v7 call, normalized to the watch schema.
    None = batch path unavailable (caller falls back to FMP)."""
    if not _yahoo["session"] and not _yahoo_auth():
        return None
    try:
        r = _yahoo["session"].get(
            "https://query1.finance.yahoo.com/v7/finance/quote",
            params={"symbols": ",".join(symbols), "crumb": _yahoo["crumb"]},
            timeout=10)
        if r.status_code != 200:
            _yahoo.update(session=None, crumb=None, next_try=time.time() + 600)
            return None
        rows = r.json().get("quoteResponse", {}).get("result", [])
    except Exception:  # noqa: BLE001
        _yahoo.update(session=None, crumb=None, next_try=time.time() + 300)
        return None
    out = {}
    for q in rows:
        price = _num(q.get("regularMarketPrice"))
        if price is None:
            continue
        d50, d200 = _num(q.get("fiftyDayAverage")), _num(q.get("twoHundredDayAverage"))
        out[q["symbol"]] = {
            "code": q["symbol"], "exch": q.get("fullExchangeName") or "US",
            "name": q.get("shortName") or q.get("longName"),
            "ltp": price, "prev": _num(q.get("regularMarketPreviousClose")),
            "day_pct": _num(q.get("regularMarketChangePercent")),
            "chg": _num(q.get("regularMarketChange")),
            "open": _num(q.get("regularMarketOpen")),
            "high": _num(q.get("regularMarketDayHigh")),
            "low": _num(q.get("regularMarketDayLow")),
            "ttq": _num(q.get("regularMarketVolume")),
            "yhigh": _num(q.get("fiftyTwoWeekHigh")), "ylow": _num(q.get("fiftyTwoWeekLow")),
            "vs50": ((price - d50) / d50 * 100) if d50 else None,
            "vs200": ((price - d200) / d200 * 100) if d200 else None,
            "mcap": _num(q.get("marketCap")),
            "ts": datetime.now().strftime("%H:%M:%S"),
        }
    return out


def fmp_get(path, **params):
    """One FMP stable-API call; None on any failure."""
    key = os.getenv("FMP_API_KEY", "").strip()
    if not key:
        return None
    params["apikey"] = key
    try:
        r = requests.get(f"https://financialmodelingprep.com/stable/{path}",
                         params=params, timeout=12)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:  # noqa: BLE001
        return None


# ---- symbol search (the add-box dropdown: confirm before adding) -------------
def search_symbols(q, region):
    q = (q or "").strip().upper()
    if not q:
        return []
    out = []
    if region == "us":
        rows = fmp_get("search-symbol", query=q, limit=10) or []
        if not rows:
            rows = fmp_get("search-name", query=q, limit=10) or []
        rows.sort(key=lambda r: ("." in (r.get("symbol") or ""), len(r.get("symbol") or "")))
        for r in rows[:8]:
            if r.get("symbol"):
                out.append({"code": r["symbol"], "name": r.get("name") or "",
                            "exch": r.get("exchange") or ""})
        if not out:                         # no feed key (or nothing back): Yahoo's search, by name or ticker
            us_venues = ("NYSE", "NASDAQ", "NYSEARCA", "AMEX", "BATS", "CBOE", "NYQ", "NMS", "NGM", "NCM", "PCX", "ASE", "BTS")
            for h in symbol_search(q)["hits"]:
                if "." not in (h["symbol"] or "") and (not h["exch"] or any(v in h["exch"].upper() for v in us_venues)):
                    out.append({"code": h["symbol"], "name": h["name"], "exch": h["exch"]})
            out = out[:8]
    elif region == "global":
        for h in symbol_search(q)["hits"][:8]:
            out.append({"code": h["symbol"], "name": h["name"], "exch": f"{h.get('type') or ''} · {h['exch']}"})
    else:                               # home: the broker's master, else Yahoo in the home market
        hook = _hook("search", live=False)
        if hook:
            try:
                return hook(q)
            except Exception:  # noqa: BLE001
                pass
        m = _market()
        try:
            resp = requests.get(
                "https://query1.finance.yahoo.com/v1/finance/search",
                params={"q": q, "quotesCount": 20, "newsCount": 0},
                headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        except Exception:  # noqa: BLE001
            resp = {}
        wanted = set()
        if m:
            wanted = {m.ysym("X", e)[1:] for e in m.META["exchanges"]}   # the suffixes (".NS")
            wanted.discard("")
        for r in resp.get("quotes", []):
            sym = r.get("symbol") or ""
            if not sym or (r.get("quoteType") or "EQUITY") != "EQUITY":
                continue
            suffix = sym[sym.rfind("."):] if "." in sym else ""
            if wanted and suffix not in wanted:
                continue
            code = sym if not wanted else sym[: sym.rfind(".")]
            out.append({"code": code, "name": r.get("shortname") or r.get("longname") or "",
                        "exch": r.get("exchange") or "", "ysym": sym})
            if len(out) >= 8:
                break
    return out


# ---- ticker research page ----------------------------------------------------
TICKER_TTL = 600
_ticker_cache = {}


def us_book_positions():
    """The US names on Desk · Book, the one hand-kept book: a symbol Yahoo lists
    with no market suffix (AAPL, BRK-B), with shares, and not a shipped example.
    The separate US file was folded into Desk · Book on 2026-09-16."""
    out = []
    for p in load_book().get("positions", []):
        sym = str(p.get("symbol") or "").upper().strip()
        try:
            shares = float(p.get("shares") or 0)
            avg = float(p.get("avg_cost") or 0)
        except (TypeError, ValueError):
            continue
        if not sym or shares == 0 or "." in sym or p.get("example"):
            continue
        out.append({"symbol": sym, "name": p.get("name") or "", "shares": shares, "avg_cost": avg})
    return out


def held_sets():
    """Every name the desk can see the reader holds or watches: Desk · Book, the
    broker's last snapshot, and the three watch grids. Symbols and broker codes, upper case."""
    book, watch = set(), set()
    try:
        for p in load_book().get("positions", []):
            if p.get("symbol") and p.get("shares"):
                book.add(str(p["symbol"]).upper())
    except (OSError, ValueError):
        pass
    snap = load_last_snapshot() or {}
    for acc in ((snap.get("data") or {}).get("accounts") or {}).values():
        for row in acc.get("equity") or []:
            if row.get("code"):
                book.add(str(row["code"]).upper())
    for loader in (load_watchlist, load_watchlist_us, load_watchlist_global):
        try:
            for e in loader():
                code = e.get("code") if isinstance(e, dict) else e
                if code:
                    watch.add(str(code).upper())
        except Exception:  # noqa: BLE001
            pass
    return {"book": book, "watch": watch}


WATCH_LABEL = {"us": "Watch · US", "global": "Global", "home": "Watch · Home"}


def journal(what, symbol="", text=""):
    """One moment for the journal; never raises, because the journal must never stop the desk."""
    try:
        return desk_notes.journal_event(what, symbol, text)
    except Exception as exc:  # noqa: BLE001
        return {"mode": "error", "written": False, "pending": None, "error": str(exc)[:120]}


def note_moment(note):
    """The journal line for a note just saved: what sort, its title, its period."""
    t, title, per = note.get("type", "general"), note.get("title", ""), note.get("period", "")
    tail = (f", {per}" if per else "") + (" (with a file)" if note.get("file") and t not in ("document", "model", "clipping") else "")
    if t == "answer":
        text = f'answer kept: "{title}"'
    elif t in ("document", "model", "clipping"):
        text = f'{t} brought in: "{title}"'
    elif t == "project":
        text = f'project started: "{title}"'
    else:
        text = f'{ {"concall": "call", "general": ""}.get(t, t) } note saved: "{title}"'.replace("  ", " ").strip()
    return text + tail


def calendar_rows():
    """Results dates the desk already holds (the Calendar on every name, the US earnings
    countdown and the home market's calendar), from the cache only: tasks never wait on a feed."""
    rows = []
    for kind in ("earn", "results_home"):
        try:
            rows.extend((cache_peek(kind) or {}).get("rows") or [])
        except Exception:  # noqa: BLE001
            pass
    try:
        rows.extend(r for r in (cache_peek("calendar") or {}).get("upcoming") or [] if r.get("kind") == "results")
    except Exception:  # noqa: BLE001
        pass
    return rows


def calendar_universe():
    """Every name the reader holds or watches, keyed by Yahoo's symbol: Desk · Book in
    any market, the broker book through the market file, and the three watchlists."""
    uni = {}
    def put(ysym, shown, tag, name=""):
        ysym = (ysym or "").upper().strip()
        if not ysym or ysym.startswith("^") or "=" in ysym or ysym.endswith(("-USD", "-EUR", "-INR", "-GBP")):
            return          # an index, a future, a currency pair or a coin has no results date
        cur = uni.get(ysym)
        uni[ysym] = {"symbol": shown or ysym, "name": name or (cur or {}).get("name", ""),
                     "tag": "held" if (tag == "held" or (cur or {}).get("tag") == "held") else "watch"}
    for p in load_book().get("positions", []):
        try:
            if float(p.get("shares") or 0) and p.get("symbol") and not p.get("example"):
                put(p["symbol"], p["symbol"], "held", p.get("name") or "")
        except (TypeError, ValueError):
            continue
    snap = load_last_snapshot() or {}
    accounts = (snap.get("data") or {}).get("accounts") or {}
    for acct in (accounts.values() if isinstance(accounts, dict) else accounts):
        for e in acct.get("equity") or []:
            if e.get("code") and e.get("value"):
                try:
                    r = _resolve(e["code"], e.get("exch") or None)
                    put(r.get("ysym") or e["code"], e["code"], "held", e.get("name") or r.get("name") or "")
                except Exception:  # noqa: BLE001
                    put(e["code"], e["code"], "held")
    for n in load_watchlist():
        try:
            r = _resolve(n["code"], n.get("exch") or None)
            put(r.get("ysym") or n["code"], n["code"], "watch", r.get("name") or "")
        except Exception:  # noqa: BLE001
            put(n["code"], n["code"], "watch")
    for n in load_watchlist_us():
        put(n["code"], n["code"], "watch", n.get("name") or "")
    for n in load_watchlist_global():
        put(n["code"], n["code"], "watch", n.get("name") or "")
    return uni


def build_calendar():
    """The Calendar screen: results, dividends and landed filings on every name held or
    watched, plus the home market's results calendar and the macro calendar the desk holds."""
    home = (cache_peek("results_home") or {}).get("rows") or []
    macro = (cache_peek("econcal") or {}).get("rows") or []
    return calendar_desk.build(calendar_universe(), home_results=home, macro=macro)


def task_alerts():
    """Tasks due today or overdue, as rows for the alert bar. Computed as the bar is read; nothing stored."""
    try:
        v = desk_notes.tasks_view(calendar_rows())
    except Exception:  # noqa: BLE001
        return []
    today = datetime.now().strftime("%Y-%m-%d")
    out = []
    for t in v["open"]["overdue"]:
        out.append({"level": "hot", "text": f"Task overdue since {t['due']}: {t['text']}" + (f" (${t['symbol']})" if t.get("symbol") and t["symbol"] not in t["text"] else ""),
                    "ts": "", "date": today, "task": True})
    for t in v["open"]["today"]:
        out.append({"level": "", "text": f"Task due today: {t['text']}" + (f" (${t['symbol']})" if t.get("symbol") and t["symbol"] not in t["text"] else ""),
                    "ts": "", "date": today, "task": True})
    return out


# ---- live blocks inside a note. A fenced ```desk block names a block and its arguments
# ("chart AAPL 1y", "quote AAPL MSFT", "commodity rubber", "tasks AAPL"); the desk answers
# the data here and the page draws it, so a note carries live numbers next to the reader's
# words. The vocabulary is small and documented on the agent page; a plugin adds a renderer
# on the page and reads any desk address for its data.
BLOCKS = {
    "quote": "quote SYM [SYM ...]              the last price and day change of each listing",
    "chart": "chart SYM [1m|3m|6m|1y|2y|5y]    closes over the range, drawn as a line",
    "watch": "watch SYM SYM ... | watch project \"Title\"   a small grid of quotes",
    "commodity": "commodity NAME                   the commodity board's card (rubber, wti, gold)",
    "status": "status SYM                       where the name stands in your research",
    "notes": "notes SYM [N]                    your latest notes on the name",
    "tasks": "tasks [SYM]                      what is open, and due",
    "timeline": "timeline SYM                     everything about the name by period",
    "book": "book                             Desk · Book, the lines and their weights",
}
_block_quotes = {}


def cache_peek(kind):
    """What the cache holds for a kind, from memory or the disk copy, without ever building:
    a block reads what the screens already have and never makes a note wait on a feed."""
    with _locks[kind]:
        stamp, data = _cache[kind]
        if data is None and kind not in DISKLESS:
            try:
                with open(os.path.join(HIST_CACHE_DIR, f"api_{kind}.json")) as fh:
                    c = json.load(fh)
                _cache[kind] = (c["at"], c["data"])
                data = c["data"]
            except (OSError, ValueError, KeyError):
                pass
    return data


def block_quote(sym):
    """A quote for a block, kept a minute so a note with ten quotes is not ten feed calls a second."""
    now = time.time()
    hit = _block_quotes.get(sym)
    if hit and now - hit[0] < 60:
        return hit[1]
    q = None
    with _watch_lock:
        for pool in (WATCH_US, WATCH, WATCH_GLOBAL):
            if sym in pool and pool[sym].get("ltp"):
                q = dict(pool[sym])
                break
    if not q:
        q = fetch_yahoo_quote(sym) or freefeed.quote(sym)
    if q:
        q = {"symbol": sym, "name": q.get("name") or "", "price": q.get("ltp"), "day_pct": q.get("day_pct"),
             "chg": q.get("chg"), "currency": q.get("currency") or "", "ts": q.get("ts") or datetime.now().strftime("%H:%M")}
        _block_quotes[sym] = (now, q)
    return q


def resolve_block(spec):
    """One block's data. Unknown or malformed blocks answer with an error the page shows in place."""
    parts = [p for p in re.split(r"\s+", (spec or "").strip()) if p]
    if not parts:
        return {"error": "an empty block"}
    kind, args = parts[0].lower(), parts[1:]
    syms = [a.upper() for a in args if re.match(r"^[A-Za-z0-9.\-^=]{1,24}$", a)]
    out = {"kind": kind, "spec": spec.strip()}
    if kind == "quote":
        if not syms:
            return {**out, "error": "quote needs a symbol: quote AAPL"}
        out["rows"] = [block_quote(sy) or {"symbol": sy, "error": "no quote right now"} for sy in syms[:20]]
    elif kind == "chart":
        if not syms:
            return {**out, "error": "chart needs a symbol: chart AAPL 1y"}
        rng = next((a.lower() for a in args if a.lower() in ("1m", "3m", "6m", "1y", "2y", "5y", "max")), "1y")
        interval = "1d" if rng in ("1m", "3m", "6m", "1y") else "1wk"
        rows = _yahoo_candles(syms[0], {"1m": "1mo", "3m": "3mo", "6m": "6mo", "max": "max"}.get(rng, rng), interval)
        out.update({"symbol": syms[0], "range": rng, "dates": [r.get("date") for r in rows], "closes": [r.get("price") for r in rows],
                    "error": "" if rows else "no history right now (the free feed is resting; try again in a minute)"})
    elif kind == "watch":
        m = re.search(r'project\s+"([^"]+)"', spec, re.I)
        if m:
            rows = desk_notes.listing(project=m.group(1))
            syms = sorted({sy for r in rows for sy in r["symbols"] + r.get("implied_symbols", [])})
            out["project"] = m.group(1)
        if not syms:
            return {**out, "error": "watch needs symbols, or a project: watch AAPL MSFT, or watch project \"Gulf delivery\""}
        out["rows"] = [block_quote(sy) or {"symbol": sy, "error": "no quote"} for sy in syms[:30]]
    elif kind == "commodity":
        want = " ".join(args).strip().lower()
        cards = (cache_peek("commods") or {}).get("cards") or []
        hit = next((c for c in cards if c.get("id", "").lower() == want or c.get("label", "").lower() == want), None)
        if not hit:
            return {**out, "error": f"no commodity called {want!r} on the board" if want else "commodity needs a name: commodity rubber",
                    "known": [c.get("id") for c in cards][:60]}
        out["card"] = {k: hit.get(k) for k in ("id", "label", "group", "unit", "value", "date", "chg", "spark", "hi52", "lo52", "from_all_high", "stale")}
    elif kind == "status":
        if not syms:
            return {**out, "error": "status needs a symbol"}
        out["status"] = name_status(syms[0])
    elif kind == "notes":
        if not syms:
            return {**out, "error": "notes needs a symbol"}
        n = next((int(a) for a in args if a.isdigit()), 5)
        out["rows"] = desk_notes.listing(symbol=syms[0])[:max(1, min(n, 30))]
    elif kind == "tasks":
        out["tasks"] = desk_notes.tasks_view(calendar_rows(), syms[0] if syms else None)
    elif kind == "timeline":
        if not syms:
            return {**out, "error": "timeline needs a symbol"}
        out["timeline"] = desk_notes.timeline(syms[0])
    elif kind == "book":
        book = cache_peek("book") or load_book()
        out["book"] = {"positions": (book.get("positions") or [])[:60], "totals": book.get("totals") or {}, "cash": book.get("cash") or []}
    else:
        return {**out, "error": f"no block called {kind!r}", "known": sorted(BLOCKS)}
    return out


PLUGIN_LIST_URL = os.getenv("PLUGIN_LIST_URL", "https://greeksoup.ai/plugins/index.json")
_plugin_list_cache = {"at": 0.0, "data": None}


def plugin_list():
    """The public list of plugins, read from greeksoup.ai once an hour: name, what it adds, who
    wrote it, what it talks to, and the zip that brings it in. Nothing installs on its own."""
    now = time.time()
    if _plugin_list_cache["data"] is not None and now - _plugin_list_cache["at"] < 3600:
        return _plugin_list_cache["data"]
    try:
        r = requests.get(PLUGIN_LIST_URL, timeout=15)
        data = r.json()
        rows = [x for x in (data.get("plugins") or []) if isinstance(x, dict) and x.get("name") and x.get("zip")]
        out = {"ok": True, "plugins": rows, "url": PLUGIN_LIST_URL, "checked": datetime.now().strftime("%Y-%m-%d %H:%M")}
    except Exception as exc:  # noqa: BLE001
        out = {"ok": False, "plugins": [], "url": PLUGIN_LIST_URL, "error": f"the list could not be read ({type(exc).__name__})"}
    _plugin_list_cache.update(at=now, data=out)
    return out


def install_from_list(name):
    lst = plugin_list()
    row = next((x for x in lst.get("plugins", []) if x.get("name") == name), None)
    if not row:
        raise ValueError(f"{name!r} is not on the list")
    url = str(row["zip"])
    if not url.startswith("https://"):
        raise ValueError("the list points at an address that is not https; refused")
    r = requests.get(url, timeout=60)
    if r.status_code != 200:
        raise ValueError(f"the zip could not be fetched ({r.status_code})")
    return desk_plugins.install_zip(r.content, name)


def name_status(symbol):
    sets = held_sets()
    sym = (symbol or "").upper()
    return desk_notes.status_of(sym, in_book=sym in sets["book"], on_watch=sym in sets["watch"])


def _held_context(symbol):
    """Where this name sits across the books: US book position and/or watchlists."""
    ctx = {}
    for p in us_book_positions():
        if p["symbol"] == symbol:
            ctx["us_book"] = p
    return ctx


HIST_CACHE_DIR = os.path.join(HERE, "cache")
os.makedirs(HIST_CACHE_DIR, exist_ok=True)


CANDLE_RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "3y", "5y", "10y", "max"}
CANDLE_INTERVALS = {"5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}
_candle_cache = {}


def cached_candles(sym, rng, itv):
    key = (sym, rng, itv)
    hit = _candle_cache.get(key)
    now = time.time()
    if hit and now - hit[0] < 600:
        return hit[1]
    rows = _yahoo_candles(sym, rng, itv)
    out = {"symbol": sym, "range": rng, "interval": itv, "rows": rows,
           "error": "" if rows else "no bars at that size right now (the free feed is resting; try again in a minute)"}
    if rows:
        _candle_cache[key] = (now, out)
    return out


def _yahoo_candles(ysym, rng, interval):
    """Candles for any Yahoo symbol, ascending, the chart's row shape. Goes
    through freefeed first; when that is resting after a rate limit, one plain
    call of its own, so a home ticker page is not blank for five minutes
    because a US page tripped the limit."""
    _, rows = freefeed.chart(ysym, rng, interval)
    if rows:
        return rows
    try:
        r = requests.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{ysym}",
                         params={"range": rng, "interval": interval},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        res = (r.json().get("chart", {}).get("result") or [None])[0]
    except Exception:  # noqa: BLE001
        return []
    if not res:
        return []
    ts = res.get("timestamp") or []
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    off = (res.get("meta") or {}).get("gmtoffset") or 0
    daily = interval.endswith(("d", "wk", "mo"))
    out = []
    for i, t in enumerate(ts):
        c = _num((q.get("close") or [None] * len(ts))[i])
        if c is None:
            continue
        d = datetime.fromtimestamp(t + off, tz=timezone.utc)
        out.append({"date": d.strftime("%Y-%m-%d" if daily else "%Y-%m-%d %H:%M"), "price": c,
                    "o": _num((q.get("open") or [None] * len(ts))[i]),
                    "h": _num((q.get("high") or [None] * len(ts))[i]),
                    "l": _num((q.get("low") or [None] * len(ts))[i]),
                    "v": _num((q.get("volume") or [None] * len(ts))[i])})
    return out


CURRENCY_SYMBOLS = {"USD": "$", "INR": "₹", "GBP": "£", "GBp": "p", "EUR": "€", "JPY": "¥",
                    "CNY": "¥", "HKD": "HK$", "AUD": "A$", "CAD": "C$", "SGD": "S$", "CHF": "Fr",
                    "AED": "AED ", "SAR": "SAR ", "BRL": "R$", "KRW": "₩", "SEK": "kr", "NOK": "kr"}


def _daily_history_home(code, exch, years=8):
    """Daily candles for a home name, newest first, disk-cached per day: history
    changes once a session, so only the first click of the day pays. Through the
    broker's history hook when its file has one, else Yahoo through the resolved
    symbol. When neither answers (weekend, lapsed login) the stale cache is
    served rather than an empty chart."""
    today = datetime.now().strftime("%Y-%m-%d")
    cpath = os.path.join(HIST_CACHE_DIR, f"hist_{code}.json")
    stale = None
    try:
        with open(cpath) as fh:
            c = json.load(fh)
        if c.get("data"):
            if c.get("date") == today:
                return c["data"]
            stale = c["data"]
    except (OSError, ValueError):
        pass
    data = []
    hook = _hook("history")
    if hook and not broker_health["dead"]:
        try:
            data = hook(_client(), code, exch, years)
        except Exception:  # noqa: BLE001
            data = []
    if not data:
        r = _resolve(code, exch)
        if r.get("ysym"):
            rows = _yahoo_candles(r["ysym"], "10y", "1d")
            data = sorted(rows, key=lambda x: x["date"], reverse=True)
    if data:
        try:
            with open(cpath, "w") as fh:
                json.dump({"date": today, "data": data}, fh)
        except OSError:
            pass
        return data
    return stale or []


def _intraday_home(code, exch):
    """{"1D", "5D"} minute candles: the broker's when its file serves them,
    else Yahoo's 5-minute bars through the resolved symbol."""
    hook = _hook("intraday")
    if hook and not broker_health["dead"]:
        try:
            return hook(_client(), code, exch)
        except Exception:  # noqa: BLE001
            pass
    r = _resolve(code, exch)
    if not r.get("ysym"):
        return {}
    rows = _yahoo_candles(r["ysym"], "5d", "5m")
    pts = [{"date": x["date"][:16], "price": x["price"], "o": x.get("o"), "h": x.get("h"),
            "l": x.get("l"), "v": x.get("v")} for x in rows]
    days = sorted({p["date"][:10] for p in pts})
    return {"1D": [p for p in pts if p["date"][:10] in days[-1:]],
            "5D": [p for p in pts if p["date"][:10] in days[-5:]]}


def build_ticker_home(code):
    """The research view for a home-market name: quote, candles, intraday, the
    name and exchange, the reader's positions in it (labelled by account
    number), the futures book where the broker serves one, and the labels the
    market file gives the filings block."""
    r = _resolve(code)
    exch = r.get("exch") or ""
    q = _home_quote(code, exch or None, tries=3)
    if not q:
        return {"symbol": code, "region": "home",
                "error": f"no quote for {code} right now; check the code, or try again in a minute"}
    exch = q.get("exch") or exch
    m = _market()
    mod = ADAPTER["mod"]

    held, fut_expiries = {}, []
    for account, cli in (clients.items() if (mod and not broker_health["dead"]) else []):
        label = ACCOUNT_LABELS.get(account, account)
        amod = _mod_of(account)
        if not amod or desk_of(amod.META.get("region", "")) != "home":
            continue      # a home name is held in a home-market account; the US and global desks have their own
        try:
            for e in amod.equity(cli):
                if e["code"] == code:
                    held[label] = e
            for f in (amod.futures(cli) if hasattr(amod, "futures") else []):
                if (f.get("underlying") or "") == code:
                    held[f"{label} · futures"] = f
                    if f.get("expiry") and f["expiry"] not in fut_expiries:
                        fut_expiries.append(f["expiry"])
        except Exception:  # noqa: BLE001
            pass

    futures_quotes = []
    fq_hook = _hook("futures_quote")
    for exp in (fut_expiries if fq_hook else []):
        fq = fq_hook(_client(), code, exp)
        if fq:
            futures_quotes.append(fq)

    meta = dict(r.get("meta") or {})
    meta.setdefault("company", r.get("name") or q.get("name") or "")
    meta.setdefault("exch", exch)
    cur_code = q.get("currency") or ""
    return {
        "symbol": code, "region": "home",
        "exchange_symbol": r.get("symbol") if r.get("symbol") != code else "",
        "ysym": r.get("ysym", ""),
        # the sign follows the quote's own currency (an NSE name is rupees whatever the home market); the market's sign only when the feed names none
        "currency_symbol": (CURRENCY_SYMBOLS.get(cur_code, cur_code + " ") if cur_code and (not m or cur_code != m.META["currency"]) else (m.META["symbol"] if m else "")),
        "filings": (m.META.get("filings") if m else "") or "",
        "units": (m.META.get("units") if m else "") or "",
        "market": (m.META["label"] if m else ""),
        "has_book": q.get("bid") is not None,
        "meta": meta, "quote": q,
        "history": _daily_history_home(code, exch),
        "intraday": _intraday_home(code, exch),
        "futures_quotes": futures_quotes,
        "held_in": held,
        "ts": datetime.now().strftime("%H:%M:%S"),
    }


def _trim_ohlcv(rows):
    """Full-EOD rows to the compact OHLCV shape the chart eats. Newest-first."""
    out = []
    for r in rows or []:
        c = _num(r.get("close") if "close" in r else r.get("price"))
        if c is None:
            continue
        out.append({"date": r.get("date"), "price": c,
                    "o": _num(r.get("open")), "h": _num(r.get("high")),
                    "l": _num(r.get("low")), "v": _num(r.get("volume"))})
    return out


def _us_intraday(rows):
    """FMP 5-min bars -> the same {1D, 5D} shape the India pages use; the chart
    frontend then shows the 1D/5D tabs on US names too."""
    pts = []
    for r in rows or []:
        c = _num(r.get("close"))
        if c is None:
            continue
        pts.append({"date": (r.get("date") or "")[:16], "price": c,
                    "o": _num(r.get("open")), "h": _num(r.get("high")),
                    "l": _num(r.get("low")), "v": _num(r.get("volume"))})
    pts.sort(key=lambda p: p["date"])
    days = sorted({p["date"][:10] for p in pts})
    return {"1D": [p for p in pts if p["date"][:10] in days[-1:]],
            "5D": [p for p in pts if p["date"][:10] in days[-5:]]}


def build_ticker(symbol):
    """Aggregate the full research view for one US symbol. The ~12 FMP calls
    run IN PARALLEL (his 'too slow' feedback: was 4-6s sequential, now ~1s),
    cached TICKER_TTL seconds."""
    frm = "2005-01-01"  # MAX range; the chart slices shorter windows client-side
    first = lambda x: (x[0] if isinstance(x, list) and x else {})  # noqa: E731
    jobs = {
        "quote": ("quote", {"symbol": symbol}),
        "profile": ("profile", {"symbol": symbol}),
        "ratios": ("ratios-ttm", {"symbol": symbol}),
        "metrics": ("key-metrics-ttm", {"symbol": symbol}),
        "history": ("historical-price-eod/full", {"symbol": symbol, "from": frm}),
        "intra": ("historical-chart/5min", {"symbol": symbol}),
        "news": ("news/stock", {"symbols": symbol, "limit": 14}),
        "pt": ("price-target-summary", {"symbol": symbol}),
        "grades": ("grades-consensus", {"symbol": symbol}),
        "earnings": ("earnings", {"symbol": symbol, "limit": 6}),
        "insiders": ("insider-trading/search", {"symbol": symbol, "limit": 12}),
        "dividends": ("dividends", {"symbol": symbol, "limit": 4}),
    }
    res = {}
    if os.getenv("FMP_API_KEY", "").strip():
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {k: ex.submit(fmp_get, path, **params) for k, (path, params) in jobs.items()}
            for k, f in futs.items():
                res[k] = f.result()
    quote = first(res.get("quote"))
    if not quote.get("price"):
        # No feed key, or the feed had nothing: the keyless path. Quote and
        # candles from Yahoo, the insider table straight from EDGAR.
        page = freefeed.ticker(symbol)
        if not page.get("error"):
            try:
                page["insiders"] = sec_form4.for_ticker(symbol)
            except Exception:  # noqa: BLE001
                page["insiders"] = []
            page["held"] = _held_context(symbol)
        return page
    return {
        "symbol": symbol,
        "quote": quote,
        "profile": first(res["profile"]),
        "ratios": first(res["ratios"]),
        "metrics": first(res["metrics"]),
        "history": _trim_ohlcv(res["history"]),
        "intraday": _us_intraday(res["intra"]),
        "news": res["news"] or [],
        "pt": first(res["pt"]),
        "grades": first(res["grades"]),
        "earnings": res["earnings"] or [],
        "insiders": res["insiders"] or [],
        "dividends": res["dividends"] or [],
        "held": _held_context(symbol),
        "ts": datetime.now().strftime("%H:%M:%S"),
    }


INFUND_TTL = 12 * 3600
_infund_cache = {}
_infund_lock = threading.Lock()


def cached_infund(code):
    """The filings block of the home ticker page (results, shareholding,
    announcements) from the market file. Per-symbol, disk-backed, 12h; never
    caches a failure to reach the exchange."""
    m = _market()
    if not m or not hasattr(m, "fundamentals"):
        return {"error": "no filings feed for this market yet"}
    sym = _resolve(code).get("symbol")
    if not sym:
        return {"error": "no exchange listing mapped for this code, so no filings feed here"}
    now = time.time()
    with _infund_lock:
        hit = _infund_cache.get(code)
    if hit and now - hit[0] < INFUND_TTL:
        return hit[1]
    dpath = os.path.join(HIST_CACHE_DIR, f"api_infund_{code}.json")
    if not hit:
        try:
            with open(dpath) as fh:
                c = json.load(fh)
            if now - c["at"] < INFUND_TTL:
                with _infund_lock:
                    _infund_cache[code] = (c["at"], c["data"])
                return c["data"]
        except (OSError, ValueError, KeyError):
            pass
    data = m.fundamentals(sym)
    if data is None:
        return {"error": "the exchange is not answering right now; reload to retry"}
    with _infund_lock:
        _infund_cache[code] = (now, data)
    try:
        with open(dpath, "w") as fh:
            json.dump({"at": now, "data": data}, fh)
    except OSError:
        pass
    return data


def _ticker_from_commodity(symbol):
    """The commodity board already holds this contract's level and ten years of its
    record: when the free feed is resting, the ticker page opens from that copy (the
    board's own cache on disk, never a new request) rather than an empty screen."""
    try:
        with open(os.path.join(HIST_CACHE_DIR, "api_commods.json")) as fh:
            cards = (json.load(fh).get("data") or {}).get("cards") or []
    except (OSError, ValueError, AttributeError):
        return None
    card = next((c for c in cards if c.get("ysym") == symbol and c.get("value")), None)
    if not card:
        return None
    full = card.get("full") or []
    hist = [{"date": d, "price": v, "o": None, "h": None, "l": None, "v": None}
            for d, v in reversed(full) if v is not None]
    price = card["value"]
    chg = (card.get("chg") or {}).get("1d")
    prev = price / (1 + chg / 100.0) if chg is not None and chg > -100 else None
    return {
        "symbol": symbol, "region": "global",
        "quote": {"symbol": symbol, "price": price, "previousClose": prev,
                  "change": (price - prev) if prev else None, "changePercentage": chg,
                  "yearHigh": (card.get("hi52") or {}).get("v"), "yearLow": (card.get("lo52") or {}).get("v"),
                  "name": card.get("label"), "exchange": card.get("src_live") or ""},
        "profile": {"companyName": card.get("label"), "exchange": card.get("src_live") or "",
                    "sector": card.get("group"), "industry": (card.get("unit") or "")},
        "ratios": {}, "metrics": {}, "history": hist, "intraday": {"1D": [], "5D": []},
        "news": [], "pt": {}, "grades": {}, "earnings": [], "insiders": [], "dividends": [],
        "source": "commodity board", "ts": datetime.now().strftime("%H:%M:%S"),
        "stale_since": card.get("date") or "", "stale_why": "the free feed is resting; this is the commodity board's own copy of the record",
    }


def cached_ticker(symbol, region="us"):
    now = time.time()
    # a home click on a name from another market's exchange (SAP.DE, 7203.T on an Indian home)
    # is the free feed's page, not the home market's: its blocks (the exchange's results and
    # filings, shareholding) belong to home names only
    if region == "home" and "." in symbol:
        m = _market()
        if not (m and hasattr(m, "from_ysym") and m.from_ysym(symbol)):
            region = "global"
    key = f"{region}:{symbol}"
    hit = _ticker_cache.get(key)
    if hit and now - hit[0] < TICKER_TTL:
        return hit[1]
    # "us" and "global" are the free feed's own path (any Yahoo symbol: AAPL, SAP.DE, CL=F);
    # only the home region goes through the home market's broker and files
    data = build_ticker(symbol) if region in ("us", "global") else build_ticker_home(symbol)
    if data.get("error") and symbol.endswith("=F"):
        board = _ticker_from_commodity(symbol)
        if board:
            return board            # the board's copy; not cached, the next click asks the feed again
    # a contract, an index or an FX pair is spelt the feed's way already (CL=F, ^NSEI, EURUSD=X):
    # the name search below would hand it a company that shares its letters (CL=F became CLF)
    if data.get("error") and not any(ch in symbol for ch in "=^"):
        # a name typed as its home code (HDFCBANK, INFY), as words (HDFC Bank), or on a desk
        # with no market file for it: the free feed's search finds the exchange symbol
        # (HDFCBANK.NS) and the page shows that one, saying which name it matched
        try:
            hits = freefeed.search(symbol, 4)
        except Exception:  # noqa: BLE001
            hits = []
        pick = next((h for h in hits if h["code"].upper() != symbol), None)
        if pick:
            alt = build_ticker(pick["code"].upper())
            if not alt.get("error"):
                alt["matched_from"] = symbol
                alt["region"] = "us"
                data = alt
    dpath = os.path.join(HIST_CACHE_DIR, f"api_ticker_{re.sub(r'[^A-Za-z0-9.^=-]', '_', key)}.json")
    if not data.get("error"):        # never cache a failure; retry next click
        data.setdefault("region", region)   # the page renders by the answer, not the door it came in by
        _ticker_cache[key] = (now, data)
        try:
            with open(dpath, "w") as fh:
                json.dump({"at": now, "data": data}, fh)
        except OSError:
            pass
        return data
    # the feed is resting or the name is off the air: the last full read of this page, from
    # disk, with the time it was taken, rather than a blank screen
    try:
        with open(dpath) as fh:
            c = json.load(fh)
        if now - c["at"] < 7 * 86400 and not c["data"].get("error"):
            stale = dict(c["data"])
            stale["stale_since"] = datetime.fromtimestamp(c["at"]).strftime("%Y-%m-%d %H:%M")
            stale["stale_why"] = data.get("error", "")
            return stale
    except (OSError, ValueError, KeyError):
        pass
    return data


# ---- financials layer (statements / ratios / segments / estimates / peers) --
FIN_TTL = 12 * 3600
_fin_cache = {}
_fin_lock = threading.Lock()


def build_fin(symbol):
    """The fundamentals bundle for one US symbol: all three statements
    (annual + quarterly), annual ratio/metric history, segment mix, forward
    estimates, dividend history, a peer comparison, and the pieces the
    client-side DCF workspace seeds from. All single-symbol Starter calls
    (batch is gated), run in parallel, cached 12h per symbol."""
    jobs = {
        "inc_a": ("income-statement", {"symbol": symbol, "limit": 6}),
        "inc_q": ("income-statement", {"symbol": symbol, "period": "quarter", "limit": 8}),
        "bs_a": ("balance-sheet-statement", {"symbol": symbol, "limit": 6}),
        "bs_q": ("balance-sheet-statement", {"symbol": symbol, "period": "quarter", "limit": 8}),
        "cf_a": ("cash-flow-statement", {"symbol": symbol, "limit": 6}),
        "cf_q": ("cash-flow-statement", {"symbol": symbol, "period": "quarter", "limit": 8}),
        "ratios": ("ratios", {"symbol": symbol, "limit": 6}),
        "metrics": ("key-metrics", {"symbol": symbol, "limit": 6}),
        "est_a": ("analyst-estimates", {"symbol": symbol, "period": "annual", "limit": 10}),
        "seg_p": ("revenue-product-segmentation", {"symbol": symbol}),
        "seg_g": ("revenue-geographic-segmentation", {"symbol": symbol}),
        "peers": ("stock-peers", {"symbol": symbol}),
        "divs": ("dividends", {"symbol": symbol, "limit": 40}),
        "dcf": ("discounted-cash-flow", {"symbol": symbol}),
        "scores": ("financial-scores", {"symbol": symbol}),
    }
    res = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {k: ex.submit(fmp_get, path, **params) for k, (path, params) in jobs.items()}
        for k, f in futs.items():
            try:
                res[k] = f.result()
            except Exception:  # noqa: BLE001
                res[k] = None
    if not (res.get("inc_a") or []):
        # no provider, or a name the provider does not carry: the three statements from the
        # free record, four annual and four quarterly periods, for any listed company anywhere
        free = freefeed.statements(symbol)
        if free.get("inc_a") or free.get("bs_a"):
            return {"symbol": symbol, "free": True, "currency": free.get("currency") or "",
                    "inc_a": free["inc_a"], "inc_q": free["inc_q"], "bs_a": free["bs_a"], "bs_q": free["bs_q"],
                    "cf_a": free["cf_a"], "cf_q": free["cf_q"],
                    "note": ("The statements come from the free record: the last four years and four quarters, fewer lines than a data provider gives. "
                             + ("Ratio history, segments, estimates and peers need a data provider; none is set." if not os.getenv("FMP_API_KEY", "").strip()
                                else "The data provider does not carry this name; ratio history, segments, estimates and peers need one that does."))}
        if not os.getenv("FMP_API_KEY", "").strip():
            return {"symbol": symbol, "no_provider": True,
                    "error": "The free record carries no statements for this name, and the ratio history, segments, estimates and peers need a data provider, which is not set. The quote, the chart, valuation and quality above come from the free record."}
        return {"symbol": symbol, "error": f"Neither the data provider nor the free record carries statements for {symbol}."}

    # peer comparison rows: the name itself first, then up to 8 FMP peers,
    # each priced from quote + TTM ratios (single-symbol calls)
    peer_syms = [symbol] + [p.get("symbol") for p in (res.get("peers") or [])[:8]
                            if p.get("symbol") and p.get("symbol") != symbol]

    def _peer_row(sym2):
        try:
            q = (fmp_get("quote", symbol=sym2) or [{}])[0]
            r = (fmp_get("ratios-ttm", symbol=sym2) or [{}])[0]
        except Exception:  # noqa: BLE001
            return None
        if not q.get("price"):
            return None
        return {"symbol": sym2, "name": q.get("name") or "",
                "mktCap": q.get("marketCap"), "price": q.get("price"),
                "pe": r.get("priceToEarningsRatioTTM"),
                "ps": r.get("priceToSalesRatioTTM"),
                "pb": r.get("priceToBookRatioTTM"),
                "evx": r.get("enterpriseValueMultipleTTM"),
                "gm": r.get("grossProfitMarginTTM"),
                "om": r.get("operatingProfitMarginTTM"),
                "nm": r.get("netProfitMarginTTM"),
                "de": r.get("debtToEquityRatioTTM"),
                "divy": r.get("dividendYieldPercentageTTM")}
    with ThreadPoolExecutor(max_workers=8) as ex:
        peer_rows = [r for r in ex.map(_peer_row, peer_syms) if r]

    first = lambda x: (x[0] if isinstance(x, list) and x else {})  # noqa: E731
    return {"symbol": symbol,
            "inc_a": res.get("inc_a") or [], "inc_q": res.get("inc_q") or [],
            "bs_a": res.get("bs_a") or [], "bs_q": res.get("bs_q") or [],
            "cf_a": res.get("cf_a") or [], "cf_q": res.get("cf_q") or [],
            "ratios": res.get("ratios") or [], "metrics": res.get("metrics") or [],
            "est_a": res.get("est_a") or [],
            "seg_p": res.get("seg_p") or [], "seg_g": res.get("seg_g") or [],
            "divs": res.get("divs") or [], "peers": peer_rows,
            "dcf": first(res.get("dcf")), "scores": first(res.get("scores")),
            "ts": datetime.now().strftime("%H:%M:%S")}


def cached_fin(symbol):
    """Per-symbol, disk-backed 12h cache; never caches a failure."""
    now = time.time()
    with _fin_lock:
        hit = _fin_cache.get(symbol)
    if hit and now - hit[0] < FIN_TTL:
        return hit[1]
    dpath = os.path.join(HIST_CACHE_DIR, f"api_fin_{symbol}.json")
    if not hit:
        try:
            with open(dpath) as fh:
                c = json.load(fh)
            if now - c["at"] < FIN_TTL:
                with _fin_lock:
                    _fin_cache[symbol] = (c["at"], c["data"])
                return c["data"]
        except (OSError, ValueError, KeyError):
            pass
    data = build_fin(symbol)
    if data.get("error"):
        return data
    with _fin_lock:
        _fin_cache[symbol] = (now, data)
    try:
        with open(dpath, "w") as fh:
            json.dump({"at": now, "data": data}, fh)
    except OSError:
        pass
    return data


# ---- global watch (Yahoo, keyless) ------------------------------------------
WATCHLIST_GLOBAL_PATH = os.path.join(DATA_DIR, "watchlist_global.json")
WATCH_GLOBAL = {}


def load_watchlist_global():
    try:
        with open(WATCHLIST_GLOBAL_PATH) as fh:
            return json.load(fh).get("names", [])
    except OSError:
        return []


def save_watchlist_global(names):
    with open(WATCHLIST_GLOBAL_PATH, "w") as fh:
        json.dump({"_comment": "Edit in the Watch Global page. Yahoo symbols "
                   "(TALABAT.AE, 0700.HK, MC.PA ...).", "format": 1, "names": names}, fh, indent=2)


def fetch_yahoo_quote(symbol):
    """Quote from Yahoo's public chart API. Keyless; be a polite guest."""
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"range": "5d", "interval": "1d"},
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        res = r.json().get("chart", {}).get("result")
        if not res:
            return None
        m = res[0].get("meta", {})
        price = _num(m.get("regularMarketPrice"))
        # chartPreviousClose is the close before the five-day range, not the last
        # session's; the previous close is the second-last daily close in the answer
        closes = [_num(c) for c in (((res[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])]
        closes = [freefeed.tidy(c) for c in closes if c is not None]     # single-precision noise off
        prev = closes[-2] if len(closes) >= 2 else freefeed.tidy(_num(m.get("previousClose")) or _num(m.get("chartPreviousClose")))
        if price is None:
            return None
        return {
            "code": symbol, "exch": m.get("exchangeName") or "",
            "name": m.get("longName") or m.get("shortName"),
            "currency": m.get("currency") or "",
            "ltp": price, "prev": prev,
            "day_pct": ((price - prev) / prev * 100) if prev else None,
            "high": _num(m.get("regularMarketDayHigh")),
            "low": _num(m.get("regularMarketDayLow")),
            "ttq": _num(m.get("regularMarketVolume")),
            "yhigh": _num(m.get("fiftyTwoWeekHigh")),
            "ylow": _num(m.get("fiftyTwoWeekLow")),
            "ts": datetime.now().strftime("%H:%M:%S"),
        }
    except Exception:  # noqa: BLE001
        return None


def global_watch_loop():
    first_cycle = True
    while True:
        for entry in load_watchlist_global():
            q = fetch_yahoo_quote(entry["code"])
            if q:
                with _watch_lock:
                    WATCH_GLOBAL[entry["code"]] = q
            time.sleep(1.5 if first_cycle else 3)   # keyless API: gentle after the fill
        first_cycle = False
        time.sleep(90)      # a full pass every two minutes or so: the free feed is delayed on most of these exchanges anyway


def build_usbook():
    """The US side of Desk · Book, priced live: the panel on Desk · Home."""
    book = load_book()
    rows = []
    for p in us_book_positions():
        q = None
        with _watch_lock:
            q = WATCH_US.get(p["symbol"])
        if not q:
            q = fetch_us_quote(p["symbol"]) or freefeed.quote(p["symbol"])
        ltp = q["ltp"] if q else None
        value = ltp * p["shares"] if ltp is not None else None
        cost = p["avg_cost"] * p["shares"]
        rows.append({
            **p, "ltp": ltp, "value": value,
            "day_pct": q.get("day_pct") if q else None,
            "pnl": (value - cost) if value is not None else None,
            "pnl_pct": ((value - cost) / cost * 100) if (value is not None and cost) else None,
        })
    deployed = sum(r["value"] for r in rows if r["value"] is not None)
    cash = sum(float(c.get("amount") or 0) for c in book.get("cash", [])
               if str(c.get("currency", "")).upper() == "USD")
    total = deployed + cash
    # The US desk sits on Desk · Home only where it has something of the reader's: the home
    # market is the US, a US broker is connected, a US name is on Desk · Book, or the reader put a
    # name of their own on Watch · US (the ten starters that ship do not count). Elsewhere Home
    # stays the home market's, with one line saying how the US desk gets there.
    m = _market()
    us_broker = any(str(mod.META.get("region", "")).lower() == "us" for mod in MODS.values() if mod is not None)
    added = [n["code"] for n in load_watchlist_us() if n["code"] not in US_WATCH_STARTERS]
    show = bool(rows) or (m is not None and m.META.get("id") == "us") or us_broker or bool(added)
    return {
        "cash": cash, "positions": rows,
        "deployed": deployed, "total": total,
        "total_pnl": sum(r["pnl"] for r in rows if r["pnl"] is not None),
        "market_open": us_market_open(),
        "show": show,
        "ts": datetime.now().strftime("%H:%M:%S"),
    }


def us_watch_loop():
    """Live-first US quotes. Preferred path: ONE Yahoo batch call for the whole
    list every 10s while the US session is open (live enough, kind to the feed) and
    every 60s closed. Fallback when Yahoo throttles the crumb: a parallel FMP
    sweep — full grid every ~10s open / 120s closed, inside Starter's rate
    budget. First pass after a start is always brisk."""
    first_cycle = True
    while True:
        names = [n["code"] for n in load_watchlist_us()]
        if not names:
            time.sleep(30)
            continue
        open_ = us_market_open()
        batch = fetch_us_batch(names)
        if batch is not None:
            if batch:
                with _watch_lock:
                    WATCH_US.update(batch)
            first_cycle = False
            time.sleep(10 if open_ else 60)     # one call for the whole list; ten seconds keeps the grid live without wearing out the free feed
            continue
        # FMP fallback: sweep in parallel, then rest
        with ThreadPoolExecutor(max_workers=8) as ex:
            for code, q in zip(names, ex.map(lambda c: fetch_us_quote(c) or freefeed.quote(c), names)):
                if q:
                    with _watch_lock:
                        WATCH_US[code] = q
        nap = 10 if (open_ or first_cycle) else 120
        first_cycle = False
        time.sleep(nap)


def _stream_healthy():
    hook = _hook("stream_healthy")
    try:
        return bool(hook and hook())
    except Exception:  # noqa: BLE001
        return False


def watch_loop():
    """Cycle the home watchlist forever, one quote at a time, latest kept in
    WATCH. Through the broker's quote hook when its file has one (gently, inside
    the broker's rate limit; slower off-hours), else Yahoo through each name's
    resolved symbol, so a reader on any broker, or none, has a home grid."""
    first_cycle = True
    while True:
        names = load_watchlist()
        quote_hook = _hook("quote")
        if quote_hook is None:
            for entry in names:
                q = _home_quote(entry["code"], entry.get("exch") or None)
                if q:
                    with _watch_lock:
                        WATCH[entry["code"]] = q
                time.sleep(1)
            first_cycle = False
            time.sleep(90)
            continue
        any_ok = False
        # names put on the list from the free feed (a Yahoo symbol, added before a broker was
        # connected or by choice) keep pricing from the free feed; the broker prices its own
        for entry in names:
            if not _is_broker_name(entry):
                q = fetch_yahoo_quote(entry["code"])
                if q:
                    with _watch_lock:
                        WATCH[entry["code"]] = q
                continue
            q = _home_quote(entry["code"], entry.get("exch") or None)
            if q:
                any_ok = True
                with _watch_lock:
                    WATCH[entry["code"]] = q
            # while live ticks are arriving this loop is only the fallback and
            # the dead-session probe, so it need not hammer the quote endpoint
            if _stream_healthy():
                time.sleep(5.0)
            else:
                time.sleep(0.7 if (home_market_open() or first_cycle) else 3.0)
        if any(_is_broker_name(e) for e in names):     # a full silent pass over the broker's names = the session is dead
            broker_health["dead"] = not any_ok         # a list with only free-feed names says nothing about the session
        # Thinly traded names often return no usable quote. For held names the
        # holdings feed carries the broker's own mark; use it rather than
        # leaving a dead row on the grid.
        with _watch_lock:
            missing = [e for e in names if _is_broker_name(e) and e["code"] not in WATCH]
        if missing and not broker_health["dead"]:
            marks = {}
            for acct, cl in clients.items():
                try:
                    for row in _mod_of(acct).equity(cl):
                        if row.get("ltp"):
                            marks[row["code"]] = row
                except Exception:  # noqa: BLE001
                    pass
            for e in missing:
                row = marks.get(e["code"])
                if row:
                    with _watch_lock:
                        WATCH[e["code"]] = {
                            "code": e["code"], "exch": e.get("exch", ""),
                            "ltp": row["ltp"], "prev": None,
                            "day_pct": row.get("day_pct"),
                            "bid": None, "bid_qty": None,
                            "offer": None, "offer_qty": None,
                            "open": None, "high": None, "low": None, "ttq": None,
                            "ts": datetime.now().strftime("%H:%M:%S"),
                        }
        first_cycle = False
        time.sleep(2)


def home_market_open():
    """The home market's regular session, from its market file; False when no
    home market is set."""
    m = _market()
    try:
        return bool(m and m.is_open())
    except Exception:  # noqa: BLE001
        return False


def _market_info():
    """What the pages need to know about the home market, in one block."""
    m = _market()
    if not m:
        return {"id": "", "label": "", "exchanges": [], "session_label": "",
                "symbol": "", "locale": "", "currency": ""}
    return {k: m.META.get(k, "") for k in
            ("id", "label", "exchanges", "session_label", "symbol", "locale", "currency",
             "benchmark_label")}


_PREV_CLOSE = {}          # ysym -> (at, prev close); a previous close changes once a day


def _prev_close_for(ysym, ttl=900):
    """The last session's close for a Yahoo symbol, kept fifteen minutes, so a
    thirty-second snapshot does not ask Yahoo for every line every time."""
    hit = _PREV_CLOSE.get(ysym)
    now = time.time()
    if hit and now - hit[0] < ttl:
        return hit[1]
    q = fetch_yahoo_quote(ysym)
    prev = (q or {}).get("prev")
    if prev:
        _PREV_CLOSE[ysym] = (now, prev)
        return prev
    return hit[1] if hit else None


def _fill_marks(rows):
    """Brokers that hand out no price get every line marked from Yahoo, and every
    line's day change is the desk's own, against the last session's close: a
    broker's own field can read zero after the close (Alpaca's change_today) or
    measure from a different base, and then Desk · Home disagreed with Watch on
    the same name."""
    for e in rows:
        if e.get("ltp") is None and e.get("ysym"):
            q = fetch_yahoo_quote(e["ysym"])
            if not q or not q.get("ltp"):
                if e.get("close_mark") is not None:
                    e["ltp"] = e["close_mark"]
            else:
                e["ltp"], e["day_pct"] = q["ltp"], q.get("day_pct")
                if q.get("prev"):
                    _PREV_CLOSE[e["ysym"]] = (time.time(), q["prev"])
        if e.get("ltp") is not None and e.get("ysym"):
            prev = _prev_close_for(e["ysym"])
            if prev:
                e["day_pct"] = (e["ltp"] - prev) / prev * 100
        if e.get("ltp") is not None:
            brokers.derive(e)
    return rows


def _reads(cli, account=None):
    """equity, futures, funds through the account's own broker file."""
    mod = _mod_of(account)
    if mod is None:
        return [], [], {}
    equity = _fill_marks(mod.equity(cli))
    futures = mod.futures(cli) if hasattr(mod, "futures") else []
    funds = mod.funds(cli) if hasattr(mod, "funds") else {}
    return equity, futures, funds


def build_snapshot():
    accounts = {}
    alive = False
    live_client = None
    for name, cli in clients.items():
        try:
            equity, futures, funds = _reads(cli, name)
        except brokers.BrokerError as exc:
            print(f"  broker: {exc}")
            equity, futures, funds = [], [], {}
        except Exception as exc:  # noqa: BLE001 - a broker outage is not a desk outage
            print(f"  broker read failed: {exc}")
            equity, futures, funds = [], [], {}
        if equity or futures or funds.get("cash") is not None:
            alive = True
            live_client = live_client or cli
        eq_value = sum(e["value"] for e in equity if e["value"] is not None)
        eq_pnl = sum(e["pnl"] for e in equity if e["pnl"] is not None)
        fno_mtm = sum(f["mtm"] for f in futures if f["mtm"] is not None)
        limit_total = funds.get("fno_limit_total")
        blocked = funds.get("fno_blocked") or 0
        amod = _mod_of(name)
        accounts[name] = {
            "label": ACCOUNT_LABELS.get(name, name),
            "broker": (amod.META["label"] if amod else ""),
            "region": (amod.META.get("region", "") if amod else ""),
            "desk": desk_of(amod.META.get("region", "") if amod else ""),
            "currency": funds.get("currency") or (equity[0].get("currency") if equity else "") or "",
            "equity": equity,
            "futures": futures,
            "funds": funds,
            "totals": {
                "equity_value": eq_value,
                "equity_pnl": eq_pnl,
                "fno_mtm": fno_mtm,
                "cash": funds.get("cash"),
                "free_limit": funds.get("fno_free"),
                "limit_total": limit_total,
                "blocked": blocked,
                "util_pct": (blocked / limit_total * 100) if limit_total else None,
            },
            "broker_at": time.time(),
        }

    # A broker file that supports several accounts hands back the others with
    # no session today: the last saved book, marks re-priced through the live
    # session, funds and margin as the broker last reported them.
    extra_hook = _hook("extra_accounts")
    if alive and extra_hook:
        live_names = [n for n, a in accounts.items()
                      if a.get("equity") or a.get("futures") or (a.get("funds") or {}).get("cash") is not None]
        try:
            extras = extra_hook(clients.get(ADAPTER["id"]) or live_client, live_names) or {}   # the home broker's other accounts
        except Exception:  # noqa: BLE001
            extras = {}
        for name, block in extras.items():
            funds = block.get("funds") or {}
            equity = block.get("equity", [])
            futures = block.get("futures", [])
            limit_total = funds.get("fno_limit_total")
            blocked = funds.get("fno_blocked") or 0
            block["totals"] = {
                "equity_value": sum(e["value"] for e in equity if e.get("value") is not None),
                "equity_pnl": sum(e["pnl"] for e in equity if e.get("pnl") is not None),
                "fno_mtm": sum(f["mtm"] for f in futures if f.get("mtm") is not None),
                "cash": funds.get("cash"),
                "free_limit": funds.get("fno_free"),
                "limit_total": limit_total,
                "blocked": blocked,
                "util_pct": (blocked / limit_total * 100) if limit_total else None,
            }
            block["label"] = ACCOUNT_LABELS.get(name) or block.get("label") or name
            block.setdefault("desk", "home")
            block.setdefault("broker", ADAPTER["mod"].META["label"] if ADAPTER["mod"] else "")
            block.setdefault("currency", funds.get("currency") or (equity[0].get("currency") if equity else "") or "")
            accounts[name] = block

    # Sparklines under the open futures, where the broker serves intraday candles.
    sparks = {}
    spark_hook = _hook("sparks")
    if alive and spark_hook:
        try:
            all_fut = [f for a in accounts.values() for f in a.get("futures", [])]
            sparks = spark_hook(live_client, all_fut) or {}
        except Exception:  # noqa: BLE001
            sparks = {}

    broker_health["dead"] = not alive
    data = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_open": home_market_open(),
        "market": _market_info(),
        "session_dead": not alive,
        "accounts": accounts,
        "sparks": sparks,
    }
    if alive:
        try:
            with open(LAST_SNAP_PATH, "w") as fh:
                json.dump({"at": time.time(), "data": data}, fh)
        except OSError:
            pass
        return data
    # Session over (lapsed login, weekend): never a blank desk. Serve the last
    # good broker book with equity marks refreshed from Yahoo's delayed quotes;
    # futures marks and every margin number stay as the broker last reported.
    return _stale_snapshot() or data


LAST_SNAP_PATH = os.path.join(HIST_CACHE_DIR, "last_snapshot.json")
_ystale = {}          # yahoo symbol -> (fetched_ts, quote)


def _yahoo_home_quote(code):
    """Delayed Yahoo quote for a home code through its resolved symbol; 10-min
    cached. A code Yahoo cannot be found for stays on the frozen mark."""
    ysym = _resolve(code).get("ysym")
    if not ysym:
        return None
    hit = _ystale.get(ysym)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    q = fetch_yahoo_quote(ysym)
    if q:
        _ystale[ysym] = (time.time(), q)
    return q


def load_last_snapshot():
    try:
        with open(LAST_SNAP_PATH) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _stale_snapshot():
    c = load_last_snapshot()
    if not c or not c.get("data", {}).get("accounts"):
        return None
    data = c["data"]
    broker_as_of = datetime.fromtimestamp(c["at"]).strftime("%a %d %b, %H:%M")
    codes = sorted({e["code"] for a in data["accounts"].values()
                    for e in a.get("equity", []) if e.get("code")})
    ysyms = {e["code"]: e.get("ysym") for a in data["accounts"].values()
             for e in a.get("equity", []) if e.get("code")}

    def _mark(code):
        ys = ysyms.get(code)
        return fetch_yahoo_quote(ys) if ys else _yahoo_home_quote(code)
    with ThreadPoolExecutor(max_workers=6) as ex:
        quotes = dict(zip(codes, ex.map(_mark, codes)))
    fresh = 0
    for a in data["accounts"].values():
        for e in a.get("equity", []):
            q = quotes.get(e.get("code"))
            if not q or not q.get("ltp"):
                continue
            fresh += 1
            e["ltp"], e["day_pct"] = q["ltp"], q.get("day_pct")
            if e.get("qty") is not None:
                e["value"] = q["ltp"] * e["qty"]
                cost = (e["avg"] * e["qty"]) if e.get("avg") is not None else None
                if cost is not None:
                    e["pnl"] = e["value"] - cost
                    e["pnl_pct"] = (e["pnl"] / cost * 100) if cost else None
        t = a.get("totals") or {}
        eq = [e for e in a.get("equity", [])]
        t["equity_value"] = sum(e["value"] for e in eq if e.get("value") is not None)
        t["equity_pnl"] = sum(e["pnl"] for e in eq if e.get("pnl") is not None)
    data["session_dead"] = True
    data["market_open"] = home_market_open()
    data["market"] = _market_info()
    data["ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["stale"] = {"broker_as_of": broker_as_of,
                     "yahoo_marks": fresh, "eq_rows": len(codes)}
    return data


def build_tape():
    """The index options tape on Desk · Home, where the broker's file serves
    option chains; an empty list otherwise and the page says so."""
    hook = _hook("tape")
    if hook is None or broker_health["dead"]:
        # nothing to read yet (no home broker, or its session is down): look again in a minute,
        # never keep an empty tape for the full ten
        return {"ts": datetime.now().strftime("%H:%M:%S"), "names": [], "_ttl": 60}
    cli = _client()
    if cli is None:
        return {"ts": datetime.now().strftime("%H:%M:%S"), "names": [], "_ttl": 60}
    try:
        names = hook(cli) or []
    except Exception as exc:  # noqa: BLE001
        return {"ts": datetime.now().strftime("%H:%M:%S"), "names": [], "_ttl": 120,
                "error": "The tape could not be read from the broker: " + str(exc)[:160]}
    return {"ts": datetime.now().strftime("%H:%M:%S"), "names": names, "_ttl": 120 if not names else None}


# ---- earnings calendar (US, FMP bulk) ---------------------------------------
def build_earnings():
    """Upcoming earnings for every US name we track (book + watchlist), one
    feed call per name. The home market's results come from its market file."""
    ours = {(p["symbol"], "held") for p in us_book_positions()}
    for n in load_watchlist_us():
        ours.add((n["code"], "watch"))
    tag = {}
    for sym, t in ours:
        tag[sym] = "held" if (tag.get(sym) == "held" or t == "held") else t
    # per-symbol (the bulk calendar truncates its universe); parallel = fast
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.getenv("FMP_API_KEY", "").strip():
        rows = freefeed.earnings(tag)
        return {"rows": rows, "ts": datetime.now().strftime("%Y-%m-%d %H:%M"), "source": "yahoo",
                "note": "" if rows else "no feed key: earnings dates come from Yahoo, which is rate-limiting right now; retry later"}

    def _next(sym):
        rows = fmp_get("earnings", symbol=sym, limit=6) or []
        fut = [e for e in rows if (e.get("date") or "") >= today]
        if not fut:
            return None
        e = min(fut, key=lambda x: x["date"])
        return {"symbol": sym, "date": e["date"], "tag": tag[sym],
                "eps_est": e.get("epsEstimated"), "rev_est": e.get("revenueEstimated")}

    out = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(_next, list(tag)):
            if r:
                out.append(r)
    out.sort(key=lambda r: r["date"])
    return {"rows": out, "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}


# ---- the home market's results calendar (from its market file) ---------------
def build_results_home():
    """Upcoming results dates for the home watchlist, from the market file's
    public calendar; cached half a day. A name the calendar cannot be found for
    is counted, not hidden. Markets without a calendar say so."""
    m = _market()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not m or not hasattr(m, "results_calendar"):
        return {"available": False, "rows": [], "skipped": 0, "ts": ts,
                "market": (m.META["label"] if m else "")}
    entries = load_watchlist()
    by_symbol = {}
    for e in entries:
        r = _resolve(e["code"], e.get("exch") or None)
        if r.get("symbol"):
            by_symbol.setdefault(r["symbol"], (e["code"], r.get("name") or ""))
    try:
        cal = m.results_calendar(list(by_symbol)) or {}
    except Exception:  # noqa: BLE001
        cal = {}
    rows = []
    for r in cal.get("rows", []):
        code, name = by_symbol.get(r.get("symbol"), (r.get("symbol"), ""))
        rows.append({**r, "code": code, "company": r.get("company") or name})
    return {"available": True, "rows": rows,
            "skipped": (cal.get("skipped") or 0) + (len(entries) - len(by_symbol)),
            "market": m.META["label"], "ts": ts}


# ---- macro (FRED, keyless CSV) ----------------------------------------------
MACRO_SERIES = [
    # (fred id, label, unit, group) — unit "%yoy" = YoY % computed from levels,
    # "k" = thousands. Groups drive the page sections. The home market's own
    # rows come from its market file.
    ("DGS2", "2Y Treasury", "%", "Rates"),
    ("DGS10", "10Y Treasury", "%", "Rates"),
    ("DGS30", "30Y Treasury", "%", "Rates"),
    ("T10Y2Y", "2s10s curve", "pp", "Rates"),
    ("FEDFUNDS", "Fed funds", "%", "Rates"),
    ("MORTGAGE30US", "30Y mortgage", "%", "Rates"),
    ("CPIAUCSL", "CPI YoY", "%yoy", "Inflation"),
    ("T10YIE", "10Y breakeven", "%", "Inflation"),
    ("T5YIFR", "5y5y fwd inflation", "%", "Inflation"),
    ("DFII10", "10Y real yield", "%", "Inflation"),
    ("UNRATE", "Unemployment", "%", "Growth & labor"),
    ("ICSA", "Initial claims", "k", "Growth & labor"),
    ("UMCSENT", "Consumer sentiment", "", "Growth & labor"),
    ("VIXCLS", "VIX", "", "Credit & vol"),
    ("BAMLH0A0HYM2", "HY spread (OAS)", "%", "Credit & vol"),
    ("BAMLC0A0CM", "IG spread (OAS)", "%", "Credit & vol"),
    ("DCOILWTICO", "WTI crude", "$", "Commodities & dollar"),
    ("DCOILBRENTEU", "Brent crude", "$", "Commodities & dollar"),
    ("DHHNGSP", "Nat gas (Henry Hub)", "$", "Commodities & dollar"),
    ("DTWEXBGS", "Dollar index", "", "Commodities & dollar"),
    ("SP500", "S&P 500", "", "Equities"),
    ("NASDAQCOM", "Nasdaq Composite", "", "Equities"),
]
desk_lists.MACRO_STARTERS = MACRO_SERIES     # the shipped set is the starter of the reader's own list


# ---- economic calendar (FMP; the Trading-Economics-style dated prints) -------
# the prints that move markets, so a country outside the reader's own and the US still shows its big ones
ECON_MAJOR = ("US", "EU", "GB", "JP", "CN", "DE")
ECON_KEY_WORDS = ("cpi", "inflation", "gdp", "rate decision", "interest rate", "policy rate", "repo", "payroll", "unemployment", "jobless",
                  "pmi", "retail sales", "trade balance", "industrial production", "fomc", "ecb", "boe", "boj", "rbi", "pboc", "consumer confidence",
                  "core pce", "pce", "ppi", "ism", "nonfarm", "employment", "central bank", "cash rate", "refi rate", "bank rate", "durable", "housing starts", "wpi", "iip")


def _econ_keep(country, event, high, countries):
    """Which prints stay: everything High or Medium at home and in the US; the prints that move markets elsewhere in the majors."""
    e = (event or "").lower()
    if country in countries:
        return True
    return country in ECON_MAJOR and (high or any(w in e for w in ECON_KEY_WORDS))


def build_econcal():
    """Upcoming macro prints, the next 60 days: the home market and the US in full, the major
    economies' market-moving prints (rate decisions, inflation, jobs, growth, PMIs). From the data
    provider when a key is set; otherwise from the free feed's own calendar. Times are UTC."""
    m = _market()
    home = (m.META.get("econ_country") if m else "") or "US"
    countries = {"US", home}
    days = 60
    frm = datetime.now().strftime("%Y-%m-%d")
    to = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    keep, source = [], ""
    rows = fmp_get("economic-calendar", **{"from": frm, "to": to}) if os.getenv("FMP_API_KEY", "").strip() else None
    if rows:
        source = "provider"
        for r in rows:
            c, imp = r.get("country"), (r.get("impact") or "")
            if c in countries and imp not in ("High", "Medium"):
                continue
            if not _econ_keep(c, r.get("event"), imp == "High", countries):
                continue
            d = str(r.get("date") or "")
            keep.append({"date": d[:10], "time": d[11:16], "country": c, "event": r.get("event"), "impact": imp or ("High" if c in ECON_MAJOR else "Medium"),
                         "estimate": r.get("estimate"), "previous": r.get("previous"), "actual": r.get("actual"), "unit": r.get("unit")})
    else:
        free = freefeed.econ_calendar(days)
        if free:
            span = max(r["date"] for r in free)
            source = "free feed" if span > (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d") else "free feed, today only"
            high = {(r["country"], r["event"], r["date"]) for r in freefeed.econ_calendar(days, high_only=True)}
            for r in free:
                is_high = (r["country"], r["event"], r["date"]) in high
                if not _econ_keep(r["country"], r["event"], is_high, countries):
                    continue
                if r["country"] in countries and not is_high and not any(w in (r["event"] or "").lower() for w in ECON_KEY_WORDS):
                    continue      # at home and in the US, the low-impact noise (rig counts, weekly mortgage index) stays out
                keep.append({**r, "impact": "High" if is_high else "Medium", "unit": ""})
    keep.sort(key=lambda r: (r["date"] or "", r.get("time") or ""))
    return {"rows": keep[:400], "days": days, "home": home, "source": source, "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "_ttl": 600 if (not keep or source.endswith("today only")) else None,     # a thin answer is retried in ten minutes, not six hours
            "note": ("" if keep else ("The free feed is resting; the calendar fills when it answers again." if not os.getenv("FMP_API_KEY", "").strip() else "The provider returned no prints for the window."))
                    if not source.endswith("today only") else "The free feed is handing out today's prints only just now; the weeks ahead fill when it answers in full again."}


def build_macro():
    """The FRED cards every reader gets, plus the home market's own rows and
    cards from its market file (India: the 10-year, the repo rate, CPI)."""
    cards = []
    m = _market()
    extra = []
    if m and hasattr(m, "macro_series"):
        try:
            extra = list(m.macro_series())
        except Exception:  # noqa: BLE001
            extra = []
    series = [(r["id"], r["label"], r.get("unit", ""), r.get("group", "Other")) for r in desk_lists.effective("macro")]
    jobs = [(sid, lambda s=sid: fred.csv(s)) for sid, *_ in series]
    jobs += [(row[0], row[4]) for row in extra]
    with ThreadPoolExecutor(max_workers=6) as ex:
        fetched = dict(zip((sid for sid, _ in jobs), ex.map(lambda j: j[1](), jobs)))
    all_series = list(series) + [tuple(row[:4]) for row in extra]
    for sid, label, unit, group in all_series:
        data = fetched.get(sid) or []
        if not data:
            continue
        if unit == "%yoy":     # CPI level -> YoY %
            data = [(d, (v / data[i - 12][1] - 1) * 100)
                    for i, (d, v) in enumerate(data) if i >= 12]
            unit = "%"
        if unit == "k":        # claims come as raw counts
            data = [(d, v / 1000) for d, v in data]
        latest_d, latest = data[-1]
        # delta vs ~1 month back; frequency from the actual date spacing (a
        # length heuristic misread long monthly series like UNRATE as daily)
        try:
            gap = (datetime.strptime(data[-1][0], "%Y-%m-%d")
                   - datetime.strptime(data[-2][0], "%Y-%m-%d")).days
        except (ValueError, IndexError):
            gap = 30
        back = 1 if gap >= 25 else (4 if gap >= 6 else 22)
        prev = data[-1 - back][1] if len(data) > back else None
        two_yr = data[-504:] if len(data) > 504 else data
        step = max(1, len(two_yr) // 110)
        spark = [round(v, 3) for _, v in two_yr[::step]]
        # full history, downsampled — feeds the click-to-expand chart
        fstep = max(1, len(data) // 480)
        full = [[d, round(v, 3)] for d, v in data[::fstep]]
        if full and full[-1][0] != latest_d:
            full.append([latest_d, round(latest, 3)])
        cards.append({"id": sid, "label": label, "unit": unit, "group": group,
                      "value": latest, "date": latest_d,
                      "delta": (latest - prev) if prev is not None else None,
                      "spark": spark, "full": full})
    if m and hasattr(m, "macro_cards"):
        try:
            cards.extend(m.macro_cards() or [])
        except Exception:  # noqa: BLE001
            pass
    return {"cards": cards, "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}


# ---- 13F tracker (SEC EDGAR direct — FMP gates this; EDGAR is free/primary) --
EDGAR_UA = {"User-Agent": "ResearchDesk research " + os.getenv("EDGAR_CONTACT", "your-email@example.com")}

# CUSIP -> US ticker via FMP search-cusip (verified working on Starter). The
# mapping never changes, so it lives on disk forever. "" means FMP answered
# "no US listing" (a real answer, cached); a failed lookup is never cached.
CUSIP_MAP_PATH = os.path.join(HIST_CACHE_DIR, "cusip_map.json")
_cusip_lock = threading.Lock()
try:
    with open(CUSIP_MAP_PATH) as _fh:
        CUSIP_MAP = json.load(_fh)
except (OSError, ValueError):
    CUSIP_MAP = {}


def _cusip_ticker(cusip):
    if not cusip or len(cusip) < 9:
        return None
    with _cusip_lock:
        if cusip in CUSIP_MAP:
            return CUSIP_MAP[cusip] or None
    rows = fmp_get("search-cusip", cusip=cusip)
    if rows is None:
        return None
    us = [r["symbol"] for r in rows
          if r.get("symbol") and "." not in r["symbol"] and "-" not in r["symbol"]]
    sym = sorted(us, key=len)[0] if us else ""
    with _cusip_lock:
        CUSIP_MAP[cusip] = sym
        try:
            with open(CUSIP_MAP_PATH, "w") as fh:
                json.dump(CUSIP_MAP, fh)
        except OSError:
            pass
    return sym or None


_shares_out = {}   # symbol -> (fetched_ts, shares outstanding)


def _shares_outstanding(symbol):
    """Shares outstanding = live marketCap / price (one FMP quote). Slow-moving,
    so cached half a day in memory; only successes are cached."""
    hit = _shares_out.get(symbol)
    if hit and time.time() - hit[0] < 12 * 3600:
        return hit[1]
    rows = fmp_get("quote", symbol=symbol)
    q = rows[0] if isinstance(rows, list) and rows else {}
    mcap, price = _num(q.get("marketCap")), _num(q.get("price"))
    so = (mcap / price) if (mcap and price) else None
    if so:
        _shares_out[symbol] = (time.time(), so)
    return so


def _edgar_json(url):
    try:
        r = requests.get(url, headers=EDGAR_UA, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:  # noqa: BLE001
        return None


def _parse_13f(cik, accession):
    """Parse one 13F filing's infotable into {key: {issuer, value, shares}},
    keyed by CUSIP-6 (issuer id) so quarter-over-quarter diffs don't break on
    name spelling. Values scale-fixed for filers still reporting thousands."""
    import re
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}"
    index = _edgar_json(f"{base}/index.json") or {}
    xml_names = [it["name"] for it in index.get("directory", {}).get("item", [])
                 if it["name"].lower().endswith(".xml")
                 and "primary_doc" not in it["name"].lower()]
    holdings = []
    for xn in xml_names:
        try:
            raw = requests.get(f"{base}/{xn}", headers=EDGAR_UA, timeout=25).text
        except Exception:  # noqa: BLE001
            continue
        if "infoTable" not in raw:
            continue
        for m in re.finditer(r"<(?:\w+:)?infoTable>(.*?)</(?:\w+:)?infoTable>", raw, re.S):
            blk = m.group(1)

            def _tag(t):
                mm = re.search(rf"<(?:\w+:)?{t}>\s*([^<]+?)\s*<", blk)
                return mm.group(1) if mm else None
            issuer, cusip = _tag("nameOfIssuer"), _tag("cusip")
            val, sh = _num(_tag("value")), _num(_tag("sshPrnamt"))
            if issuer and val:
                import html as _html
                issuer = _html.unescape(issuer)
                holdings.append({"issuer": issuer.title(), "cusip": (cusip or "").strip(),
                                 "value": val, "shares": sh or 0})
        if holdings:
            break
    if not holdings:
        return None
    agg = {}
    for h in holdings:
        key = h["cusip"][:6] if len(h["cusip"]) >= 6 else h["issuer"].upper()
        a = agg.setdefault(key, {"issuer": h["issuer"], "value": 0, "shares": 0,
                                 "cusip9": h["cusip"]})
        a["value"] += h["value"]
        a["shares"] += h["shares"]
    priced = [r["value"] / r["shares"] for r in agg.values() if r["shares"]]
    if priced and sorted(priced)[len(priced) // 2] < 2:
        for r in agg.values():
            r["value"] *= 1000
    return agg


def _fund_13f(cik, name, note):
    """Latest 13F top holdings PLUS what changed vs the prior quarter (new buys,
    exits, adds, trims) — diffed on CUSIP from two EDGAR filings. Disk-cached."""
    cpath = os.path.join(HIST_CACHE_DIR, f"13fv3_{cik}.json")
    try:
        with open(cpath) as fh:
            c = json.load(fh)
        if time.time() - c.get("fetched", 0) < 20 * 3600:
            return c["data"]
    except (OSError, ValueError):
        pass

    sub = _edgar_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if not sub:
        return None
    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    # newest filing per report period, latest two periods (amendments win: list
    # is newest-filed-first, and we keep the first seen per period)
    per_period = {}
    for i, f in enumerate(forms):
        if f in ("13F-HR", "13F-HR/A"):
            rp = recent.get("reportDate", [""] * len(forms))[i]
            if rp and rp not in per_period:
                per_period[rp] = i
    periods = sorted(per_period, reverse=True)[:2]
    if not periods:
        return None
    idx = per_period[periods[0]]
    filed = recent["filingDate"][idx]
    cur = _parse_13f(cik, recent["accessionNumber"][idx].replace("-", ""))
    if not cur:
        return None
    prev, prev_period = None, None
    if len(periods) > 1:
        prev_period = periods[1]
        prev = _parse_13f(cik, recent["accessionNumber"][per_period[prev_period]].replace("-", ""))

    total = sum(r["value"] for r in cur.values())
    changes = {"new": [], "exits": [], "adds": [], "trims": []}
    chg_by_key = {}
    if prev:
        for k, r in cur.items():
            p = prev.get(k)
            if p is None:
                chg_by_key[k] = "NEW"
                changes["new"].append({"issuer": r["issuer"], "value": r["value"]})
            elif p["shares"] and r["shares"]:
                d = (r["shares"] / p["shares"] - 1) * 100
                if d >= 10:
                    chg_by_key[k] = f"+{d:.0f}%"
                    changes["adds"].append({"issuer": r["issuer"], "pct": d})
                elif d <= -10:
                    chg_by_key[k] = f"{d:.0f}%"
                    changes["trims"].append({"issuer": r["issuer"], "pct": d})
        for k, p in prev.items():
            if k not in cur:
                changes["exits"].append({"issuer": p["issuer"], "value": p["value"]})
        changes["new"].sort(key=lambda x: -x["value"])
        changes["exits"].sort(key=lambda x: -x["value"])
        changes["adds"].sort(key=lambda x: -x["pct"])
        changes["trims"].sort(key=lambda x: x["pct"])
        for key in ("new", "exits"):
            changes[key] = changes[key][:6]
        for key in ("adds", "trims"):
            changes[key] = changes[key][:5]

    rows = sorted(cur.items(), key=lambda kv: -kv[1]["value"])
    top = [{**r, "weight": (r["value"] / total * 100) if total else None,
            "chg": chg_by_key.get(k)} for k, r in rows[:12]]

    # % of the company owned (share counts are irrelevant; ownership
    # of the business is the number that means something).
    def _ownership(r):
        ticker = _cusip_ticker(r.get("cusip9"))
        r["ticker"] = ticker
        so = _shares_outstanding(ticker) if (ticker and r.get("shares")) else None
        r["own_pct"] = (r["shares"] / so * 100) if so else None
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(_ownership, top))
    data = {"cik": cik, "name": name, "note": note, "filed": filed,
            "period": periods[0], "prev_period": prev_period,
            "positions": len(cur), "total_value": total, "top": top,
            "changes": changes if prev else None}
    try:
        with open(cpath, "w") as fh:
            json.dump({"fetched": time.time(), "data": data}, fh)
    except OSError:
        pass
    return data


def build_funds():
    funds = desk_lists.effective("funds")        # the reader's list; the shipped funds are starters
    out = []
    with ThreadPoolExecutor(max_workers=4) as ex:   # EDGAR allows 10 req/s; be modest
        futs = [ex.submit(_fund_13f, f["cik"], f["name"], f.get("note", "")) for f in funds]
        for f in futs:
            d = f.result()
            if d:
                out.append(d)
    return {"funds": out, "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}


# ---- quote persistence -------------------------------------------------------
QUOTES_SNAPSHOT = os.path.join(HIST_CACHE_DIR, "quotes_snapshot.json")


def restore_quotes():
    """Reload the last saved quote grids so a restart never blanks the watch
    pages (they used to show dashes for the ~12 min a full off-hours cycle
    takes). Quotes older than 3 days stay dropped."""
    try:
        with open(QUOTES_SNAPSHOT) as fh:
            c = json.load(fh)
        if time.time() - c.get("at", 0) > 3 * 86400:
            return
        with _watch_lock:
            WATCH.update(c.get("home") or c.get("in") or {})
            WATCH_US.update(c.get("us", {}))
            WATCH_GLOBAL.update(c.get("global", {}))
        print(f"  quotes restored: {len(WATCH)} IN / {len(WATCH_US)} US / "
              f"{len(WATCH_GLOBAL)} global (from last run)")
    except (OSError, ValueError):
        pass


def quote_saver_loop():
    while True:
        time.sleep(60)
        try:
            with _watch_lock:
                blob = {"at": time.time(), "home": dict(WATCH),
                        "us": dict(WATCH_US), "global": dict(WATCH_GLOBAL)}
            with open(QUOTES_SNAPSHOT, "w") as fh:
                json.dump(blob, fh)
        except Exception:  # noqa: BLE001
            pass


# ---- alerts engine (read-only: notifies, never acts) -------------------------
ALERTS_PATH = os.path.join(DATA_DIR, "alerts.json")
ALERTS = {"active": [], "fired": set()}   # fired keys: "YYYY-MM-DD|rule|symbol"
_alerts_lock = threading.Lock()


def _load_alert_rules():
    try:
        with open(ALERTS_PATH) as fh:
            return json.load(fh).get("rules", [])
    except (OSError, ValueError):
        return []


def _notify_mac(title, body):
    """Desktop ping via osascript. Best effort; the desk UI shows it anyway."""
    import subprocess
    try:
        safe_t = title.replace('"', "'")
        safe_b = body.replace('"', "'")
        subprocess.run(["osascript", "-e",
                        f'display notification "{safe_b}" with title "{safe_t}"'],
                       capture_output=True, timeout=5)
    except Exception:  # noqa: BLE001
        pass


ALERTS_STATE_PATH = os.path.join(HIST_CACHE_DIR, "alerts_state.json")


def _restore_alerts():
    """Reload alert state at boot so a restart neither re-pings the desktop nor
    stacks duplicate chips (the old behavior he flagged). Fired keys older than
    two days age out; the visible list stays capped."""
    try:
        with open(ALERTS_STATE_PATH) as fh:
            c = json.load(fh)
    except (OSError, ValueError):
        return
    cutoff = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    with _alerts_lock:
        ALERTS["fired"] = {k for k in c.get("fired", []) if k[:10] >= cutoff}
        ALERTS["active"] = c.get("active", [])[:40]


def _save_alerts():
    try:
        with _alerts_lock:
            blob = {"fired": sorted(ALERTS["fired"]), "active": ALERTS["active"]}
        with open(ALERTS_STATE_PATH, "w") as fh:
            json.dump(blob, fh)
    except Exception:  # noqa: BLE001
        pass


def _fire(key, level, text):
    """Register one alert (once per key per day) and ping the desktop. The
    visible list is deduped on text — a re-fire (new day, restart) refreshes
    the timestamp of the one chip instead of adding another."""
    now = datetime.now()
    full = f"{now.strftime('%Y-%m-%d')}|{key}"
    with _alerts_lock:
        if full in ALERTS["fired"]:
            return
        ALERTS["fired"].add(full)
        ALERTS["active"] = [a for a in ALERTS["active"] if a.get("text") != text]
        ALERTS["active"].insert(0, {
            "level": level, "text": text,
            "ts": now.strftime("%H:%M"), "date": now.strftime("%Y-%m-%d"),
        })
        ALERTS["active"] = ALERTS["active"][:40]
    _save_alerts()
    _notify_mac("GreekSoup desk", text)


def _eval_alerts():
    rules = _load_alert_rules()
    if not rules:
        return
    snap = _cache["snap"][1]            # reuse whatever the pages already pulled;
    earn = _cache["earn"][1]            # the engine adds no API traffic of its own
    today = datetime.now().strftime("%Y-%m-%d")

    for rule in rules:
        rtype = rule.get("type")
        try:
            if rtype == "day_move":
                thr = float(rule.get("threshold_pct") or 5)
                scope = rule.get("scope", "held")
                if scope == "held" and snap and not snap.get("session_dead"):
                    for name, a in snap.get("accounts", {}).items():
                        label = a.get("label", name)
                        for e in a.get("equity", []):
                            d = e.get("day_pct")
                            if d is not None and abs(d) >= thr:
                                _fire(f"day_move|{label}|{e['code']}", "warn" if abs(d) < thr * 1.6 else "hot",
                                      f"{e['code']} {d:+.1f}% today ({label})")
                elif scope == "watch_in":
                    with _watch_lock:
                        quotes = dict(WATCH)
                    for code, q in quotes.items():
                        d = q.get("day_pct")
                        if d is not None and abs(d) >= thr:
                            _fire(f"day_move|watch|{code}", "warn", f"{code} {d:+.1f}% today (watch)")
                elif scope == "watch_us":
                    with _watch_lock:
                        quotes = dict(WATCH_US)
                    for code, q in quotes.items():
                        d = q.get("day_pct")
                        if d is not None and abs(d) >= thr:
                            _fire(f"day_move|us|{code}", "warn", f"{code} {d:+.1f}% today (US watch)")

            elif rtype == "margin_util" and snap and not snap.get("session_dead"):
                thr = float(rule.get("threshold_pct") or 70)
                for name, a in snap.get("accounts", {}).items():
                    u = a.get("totals", {}).get("util_pct")
                    if u is not None and u >= thr:
                        _fire(f"margin|{name}", "hot",
                              f"Margin used {u:.0f}% on {a.get('label', name)}, the cushion is thinning")

            elif rtype == "fno_dte" and snap and not snap.get("session_dead"):
                lim = int(rule.get("days") or 7)
                for name, a in snap.get("accounts", {}).items():
                    for f in a.get("futures", []):
                        if not f.get("expiry"):
                            continue
                        try:
                            dte = (datetime.strptime(f["expiry"], "%d-%b-%Y") - datetime.now()).days
                        except ValueError:
                            continue
                        if 0 <= dte <= lim:
                            _fire(f"dte|{name}|{f['underlying']}|{f['expiry']}", "warn",
                                  f"{f['underlying']} futures expire in {dte}d ({a.get('label', name)})")

            elif rtype == "earnings_within" and earn:
                lim = int(rule.get("days") or 3)
                for e in earn.get("rows", []):
                    dd = (datetime.strptime(e["date"], "%Y-%m-%d") - datetime.strptime(today, "%Y-%m-%d")).days
                    if 0 <= dd <= lim and e.get("tag") == "held":
                        _fire(f"earn|{e['symbol']}|{e['date']}", "warn",
                              f"{e['symbol']} reports in {dd}d ({e['date']})")

            elif rtype == "congress_held":
                cap = _cache["capitol"][1]
                lookback = int(rule.get("days") or 4)
                if cap:
                    cutoff = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")
                    for r in cap.get("ours", []):
                        if (r["symbol"] in cap.get("held", [])
                                and (r.get("disclosed") or "") >= cutoff):
                            _fire(f"congress|{r['symbol']}|{r['name']}|{r['tx']}", "warn",
                                  f"Congress filing on held {r['symbol']}: {r['name']} "
                                  f"{r['type']} {r['amount']} (traded {r['tx']})")

            elif rtype == "insider_cluster":
                ins = _cache["insiders"][1]
                for c in (ins or {}).get("clusters", []):
                    if c.get("ours"):
                        _fire(f"inscluster|{c['symbol']}|{c['n_buyers']}", "hot",
                              f"Insider cluster on {c['symbol']}: {c['n_buyers']} buyers, "
                              f"${c['total_value']:,} ({c['first']} → {c['last']})")

            elif rtype == "activist_13d":
                act = _cache["act13d"][1]
                lookback = int(rule.get("days") or 7)
                if act:
                    cutoff = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")
                    for r in act.get("ours", []):
                        if r.get("root") != "SCHEDULE 13D" or (r.get("date") or "") < cutoff:
                            continue
                        who = ", ".join(f["name"] for f in r.get("filers", [])[:2]) or "?"
                        _fire(f"act13d|{r['symbol']}|{r['adsh']}",
                              "hot" if r.get("tag") == "held" else "warn",
                              f"{r['form']} on {'held ' if r.get('tag') == 'held' else ''}"
                              f"{r['symbol']} by {who} (filed {r['date']})")

            elif rtype == "commodity_move":
                # a commodity moved more than the threshold over the window
                # (1d, 1w, 1m, 3m, 1y). Fires once per day per commodity.
                cm = _cache["commods"][1]
                win = rule.get("window", "1m")
                thr = float(rule.get("threshold_pct") or 15)
                for c in (cm or {}).get("cards", []):
                    p = (c.get("chg") or {}).get(win)
                    if p is not None and abs(p) >= thr:
                        _fire(f"cmove|{c['id']}|{win}", "hot" if abs(p) >= thr * 1.6 else "warn",
                              f"{c['label']} {p:+.1f}% over {win} "
                              f"({c['value']:,.2f} {c.get('unit', '')})")

            elif rtype == "commodity_peak":
                # within N% of its five-year high (the vs-peak column, spoken)
                cm = _cache["commods"][1]
                within = float(rule.get("within_pct") or 3)
                for c in (cm or {}).get("cards", []):
                    f5 = c.get("from_5y_high")
                    if f5 is not None and f5 >= -within and c.get("hi5y"):
                        basis = " (monthly series)" if c.get("peak_basis") == "monthly" else ""
                        _fire(f"cpeak|{c['id']}", "warn",
                              f"{c['label']} within {abs(f5):.1f}% of its 5-year high "
                              f"{c['hi5y']['v']:,.2f} set {c['hi5y']['date'][:7]}{basis}")

            elif rtype == "price_level":
                sym = (rule.get("symbol") or "").upper()
                region = rule.get("region", "home")
                with _watch_lock:
                    q = (WATCH_US if region == "us" else WATCH_GLOBAL if region == "global" else WATCH).get(sym)
                ltp = q and q.get("ltp")
                if ltp is None:
                    continue
                above, below = rule.get("above"), rule.get("below")
                if above is not None and ltp >= float(above):
                    _fire(f"lvl|{sym}|>{above}", "warn", f"{sym} {ltp:,.2f} crossed above {above}")
                if below is not None and ltp <= float(below):
                    _fire(f"lvl|{sym}|<{below}", "hot", f"{sym} {ltp:,.2f} broke below {below}")
        except Exception:  # noqa: BLE001 - one bad rule never kills the loop
            pass


def alerts_loop():
    time.sleep(90)          # let the first snapshot/watch cycles land
    while True:
        _eval_alerts()
        time.sleep(60)


# ---- supply chain (vault research rendered live) -----------------------------
CHAIN_TTL = 180


def _chain_quote(region, code, exch=None):
    """One quote for a name on a chain, by the region's own path; None when nothing answers."""
    if region == "us":
        with _watch_lock:
            q = WATCH_US.get(code)
        return q or fetch_us_quote(code) or freefeed.quote(code)     # the keyless feed when no data key is set
    if region == "global":
        with _watch_lock:
            q = WATCH_GLOBAL.get(code)
        return q or fetch_yahoo_quote(code)
    with _watch_lock:
        q = WATCH.get(code)
    return q or _home_quote(code, exch or None)


def build_chain():
    """The reader's own chains from the vault, then the starters they have not put away, each
    name priced by its region's path. The research lives in the files; this only prices them."""
    listing = desk_chains.list_all()
    quoted = {}
    for chain in listing["chains"]:
        for layer in chain.get("layers", []):
            for nm in layer.get("names", []):
                code = nm.get("code")
                region = nm.get("region") or chain.get("region") or "home"
                if not code:
                    continue
                key = f"{region}:{code}"
                if key not in quoted:
                    try:
                        quoted[key] = _chain_quote(region, code, nm.get("exch"))
                    except Exception:  # noqa: BLE001
                        quoted[key] = None
                q = quoted[key]
                if q:
                    nm["ltp"], nm["day_pct"] = q.get("ltp"), q.get("day_pct")
    m = _market()
    return {"chains": listing["chains"], "hidden_starters": listing["hidden_starters"],
            "home": {"id": m.META["id"] if m else "home", "label": m.META["label"] if m else "Home",
                     "symbol": m.META["symbol"] if m else "", "locale": m.META.get("locale", "en-US") if m else "en-US"},
            "markets": [{"id": mm["id"], "label": mm["label"]} for mm in markets.all_meta()],
            "ts": datetime.now().strftime("%H:%M"), "session_dead": broker_health["dead"]}


def _chain_changed():
    """After an edit the next read must show the reader's file, not a cached copy: build now,
    store it (memory and disk) and let the page fetch."""
    try:
        _store("chain", build_chain())
    except Exception:  # noqa: BLE001
        _cache["chain"] = (0.0, None)


def _lists_post(self, body):
    """The reader's own lists: save a row, remove one (kept aside; a starter is put away), undo,
    the starters back. The screen that runs on the list rebuilds behind the page."""
    parts = self.path.split("/")
    kind, action = (parts[3] if len(parts) > 3 else ""), (parts[4] if len(parts) > 4 else "")
    if action == "undo":
        out = desk_lists.undo_remove(str(body.get("undo", "")))
        kind = out.get("kind", kind)
    elif kind not in desk_lists.KINDS:
        return self.send_error(404)
    elif action == "save":
        try:
            row = desk_lists.save(kind, body.get("row") or {}, str(body.get("was", "")))
        except ValueError as exc:
            return self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")
        out = {"ok": True, "row": row}
    elif action == "remove":
        out = desk_lists.remove(kind, str(body.get("key", "")))
    elif action == "starters":
        out = desk_lists.show_starters(kind)
    else:
        return self.send_error(404)
    if out.get("ok"):
        for c in desk_lists.caches_for(kind):
            if c in _cache:
                _cache[c] = (0.0, _cache[c][1])       # stale at once: the next read rebuilds behind the page
                builder = {"funds": build_funds, "act13d": build_activist, "capitol": build_capitol,
                           "macro": build_macro, "commods": build_commods, "tape": build_tape}.get(c)
                if builder:
                    _spawn(c, builder)
        out["list"] = desk_lists.view(kind)
    return self._send(json.dumps(out).encode(), "application/json")


def _chain_post(self, body):
    """The Chain screen's edits: save (the reader's own file in the vault), delete (kept aside,
    undo brings it back; a starter is put away), the starters back, and the AI draft."""
    path = self.path
    if path == "/api/chain/save":
        try:
            c = desk_chains.save(body.get("chain") or {})
        except ValueError as exc:
            return self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")
        _chain_changed()
        return self._send(json.dumps({"ok": True, "chain": c, "journal": journal("chain", "", f"saved the chain {c['title']}")}).encode(), "application/json")
    if path == "/api/chain/delete":
        out = desk_chains.delete(str(body.get("id", "")))
        _chain_changed()
        return self._send(json.dumps(out).encode(), "application/json")
    if path == "/api/chain/undo":
        out = desk_chains.undo_delete(str(body.get("undo", "")))
        _chain_changed()
        return self._send(json.dumps(out).encode(), "application/json")
    if path == "/api/chain/starters":
        out = desk_chains.show_starters()
        _chain_changed()
        return self._send(json.dumps(out).encode(), "application/json")
    if path == "/api/chain/draft":
        rd = ask_ready()
        door = str(body.get("door", "") or "") if "door" in body else rd["default_door"]
        if not door and not rd["ready"]:
            return self._send(json.dumps({"ok": False, "error": rd["why"], "settings": True}).encode(), "application/json")
        held = set()
        try:
            held = {(p.get("symbol") or "").upper() for p in load_book().get("positions", [])}
        except Exception:  # noqa: BLE001
            pass
        watched = set()
        try:
            watched = {n["code"] for n in load_watchlist()} | {n["code"] for n in load_watchlist_us()} | {n["code"] for n in load_watchlist_global()}
        except Exception:  # noqa: BLE001
            pass
        m = _market()
        mk = markets.load(str(body.get("market", ""))[:8].lower())
        out = desk_chains.draft(str(body.get("description", "")), (m.META["label"] if m else "home"),
                                held - {""}, watched, symbol=str(body.get("symbol", ""))[:24].upper(),
                                about=str(body.get("about", ""))[:80], door=door, market_label=(mk.META["label"] if mk else ""),
                                ask=lambda messages, system: desk_ai.complete(messages, system=system, max_tokens=6000, timeout=240),
                                run_door=desk_plugins.run_door)
        return self._send(json.dumps(out).encode(), "application/json")
    return self.send_error(404)


# ---- commodities (board + the priced names layer + the broker's local reads) --
def build_commods():
    """commods.build() needs no broker; this wrapper prices the exposure names
    (US names through the US feed, home names through the home quote path) and
    lets the broker's file attach local price lines where it has them."""
    d = commods.build(desk_lists.effective("commodities"))
    m = _market()
    home_sym = m.META["symbol"] if m else ""
    seen = {}
    for c in d["cards"]:
        for nm in c.get("names", []):
            key = f"{nm['region']}:{nm['code']}"
            if key not in seen:
                q = None
                if nm["region"] == "us":
                    with _watch_lock:
                        q = WATCH_US.get(nm["code"])
                    if not q:
                        q = fetch_us_quote(nm["code"]) or fetch_yahoo_quote(nm["code"])
                else:
                    with _watch_lock:
                        q = WATCH.get(nm["code"])
                    if not q:
                        q = _home_quote(nm["code"], nm.get("exch") or None)
                    if not q and "." in nm["code"]:
                        q = fetch_yahoo_quote(nm["code"])   # a Yahoo symbol in the file
                seen[key] = q
            q = seen[key]
            if q:
                nm["ltp"], nm["day_pct"] = q.get("ltp"), q.get("day_pct")
                nm["ccy"] = "$" if nm["region"] == "us" else (home_sym or q.get("currency") or "")
    # local reads belong to the broker's own market; with none connected the
    # board stays global, so a reader elsewhere never sees them
    local_hook = _hook("commodities_local")
    live_local = False
    if local_hook and not broker_health["dead"]:
        try:
            live_local = bool(local_hook(_client(), d["cards"]))
        except Exception:  # noqa: BLE001
            live_local = False
    d["local_live"] = live_local
    # the pressure ranking is rebuilt here so its rows carry the live prices
    d["pressure"] = commods.pressure(d["cards"], commods.cross_link(d["cards"]))
    return d



# ---- the hand-kept book (no broker, no feed: Yahoo symbols, any market) ------
BOOK_PATH = os.path.join(DATA_DIR, "book.json")
BOOK_TTL = 60
_book_lock = threading.Lock()


def load_book():
    try:
        with open(BOOK_PATH) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"cash": [], "positions": []}


def save_book(book):
    book.setdefault("_comment", "The hand-kept book: any symbol Yahoo Finance knows. "
                    "Edit here or in the Desk · Book page. Lines with zero shares are ignored.")
    book.setdefault("format", 1)
    with _book_lock:
        with open(BOOK_PATH, "w") as fh:
            json.dump(book, fh, indent=2)


def _book_quote(symbol):
    with _watch_lock:
        q = WATCH_GLOBAL.get(symbol)
    return q or fetch_yahoo_quote(symbol) or freefeed.quote(symbol)


def build_book():
    """Price data/book.json through Yahoo, one currency group at a time."""
    book = load_book()
    rows = []
    for p in book.get("positions", []):
        try:
            shares = float(p.get("shares") or 0)
            avg = float(p.get("avg_cost") or 0)
        except (TypeError, ValueError):
            continue
        if not p.get("symbol") or shares == 0:
            continue
        q = _book_quote(p["symbol"])
        ltp = q.get("ltp") if q else None
        prev = q.get("prev") if q else None
        value = ltp * shares if ltp is not None else None
        cost = avg * shares
        rows.append({
            "symbol": p["symbol"], "name": p.get("name") or (q or {}).get("name") or "",
            "exch": (q or {}).get("exch") or "", "currency": (q or {}).get("currency") or p.get("currency") or "",
            "shares": shares, "avg_cost": avg, "ltp": ltp, "prev": prev,
            "day_pct": (q or {}).get("day_pct"), "value": value,
            "day_pnl": ((ltp - prev) * shares) if (ltp is not None and prev) else None,
            "pnl": (value - cost) if value is not None else None,
            "pnl_pct": ((value - cost) / cost * 100) if (value is not None and cost) else None,
            "example": bool(p.get("example")),
        })
        time.sleep(0.3)      # keyless feed: polite
    cash = {c.get("currency", "").upper(): float(c.get("amount") or 0)
            for c in book.get("cash", []) if c.get("currency")}
    groups = []
    for ccy in sorted({r["currency"] for r in rows if r["currency"]} | {c for c, a in cash.items() if a}):
        rs = [r for r in rows if r["currency"] == ccy]
        val = sum(r["value"] for r in rs if r["value"] is not None)
        total = val + cash.get(ccy, 0)
        for r in rs:
            r["weight"] = (r["value"] / total * 100) if (r["value"] is not None and total) else None
        day = sum(r["day_pnl"] for r in rs if r["day_pnl"] is not None)
        prev_val = sum(r["prev"] * r["shares"] for r in rs if r["prev"])
        pnl = sum(r["pnl"] for r in rs if r["pnl"] is not None)
        cost = sum(r["avg_cost"] * r["shares"] for r in rs)
        groups.append({"currency": ccy, "n": len(rs), "value": val, "cash": cash.get(ccy, 0),
                       "total": total, "day_pnl": day,
                       "day_pct": (day / prev_val * 100) if prev_val else None,
                       "pnl": pnl, "pnl_pct": (pnl / cost * 100) if cost else None})
    # the currency most of the book sits in comes first, so the top tiles are the book's
    groups.sort(key=lambda g: -(g["total"] or 0))
    order = {g["currency"]: i for i, g in enumerate(groups)}
    rows.sort(key=lambda r: (order.get(r["currency"], 99), -(r["value"] or 0)))
    return {"positions": rows, "groups": groups,
            "all_example": bool(rows) and all(r["example"] for r in rows),
            "cash": [{"currency": c, "amount": a} for c, a in cash.items()],
            "market_note": "from Yahoo's free feed; US near live, other exchanges 15 to 20 min behind",
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}


_symsearch_cache = {}


def symbol_search(q):
    """Yahoo's free search: a name or a partial ticker in, up to eight listings out,
    each with the symbol the desk needs, the company's name and its exchange."""
    q = (q or "").strip()
    if len(q) < 1:
        return {"q": q, "hits": []}
    key = q.lower()
    hit = _symsearch_cache.get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    hits, ok = [], False
    # A plain agent string on purpose: the quote poller's browser string gets
    # rate-limited by Yahoo on busy days, and the search must still answer.
    for host in ("query2", "query1"):
        try:
            r = requests.get(f"https://{host}.finance.yahoo.com/v1/finance/search",
                             params={"q": q, "quotesCount": 8, "newsCount": 0, "listsCount": 0},
                             headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if r.status_code != 200:
                continue
            for x in r.json().get("quotes") or []:
                if x.get("quoteType") not in ("EQUITY", "ETF", "MUTUALFUND", "INDEX", "CRYPTOCURRENCY", "CURRENCY", "FUTURE"):
                    continue
                hits.append({"symbol": x.get("symbol"), "name": x.get("longname") or x.get("shortname") or "",
                             "exch": x.get("exchDisp") or x.get("exchange") or "", "type": x.get("quoteType")})
            ok = True
            break
        except Exception:  # noqa: BLE001
            continue
    out = {"q": q, "hits": hits}
    if ok:
        if len(_symsearch_cache) > 500:
            _symsearch_cache.clear()
        _symsearch_cache[key] = (time.time(), out)
    return out


def _parse_book_lines(text):
    """symbol, shares, avg cost per line; commas, tabs, semicolons or spaces;
    a header row and blank lines are skipped."""
    out, errors = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = [x.strip().strip('"') for x in re.split(r"[,\t;]+|\s{2,}|\s+(?=[\d.-])", line) if x.strip()]
        if len(parts) < 3:
            errors.append(f"'{line[:30]}' needs symbol, shares, avg cost")
            continue
        sym = parts[0].upper()
        try:
            shares, avg = float(parts[1].replace(",", "")), float(parts[2].replace(",", ""))
        except ValueError:
            if sym in ("SYMBOL", "TICKER", "SCRIP", "NAME"):
                continue          # header row
            errors.append(f"'{line[:30]}' has a non-numeric shares or cost")
            continue
        out.append({"symbol": sym, "shares": shares, "avg_cost": avg})
    return out, errors


# ---- insider cluster screener (whole-market Form 4 feed) ---------------------
INSIDERS_TTL = 6 * 3600


def build_insiders():
    """Cluster buys across the whole US tape + every open-market buy on our
    names. ~30 FMP pages per refresh; None (uncached) when the feed fails."""
    ours = {p["symbol"] for p in us_book_positions()}
    for n in load_watchlist_us():
        ours.add(n["code"])
    if not os.getenv("FMP_API_KEY", "").strip():
        return sec_form4.build(sorted(ours))
    return insiders.build(sorted(ours))


# ---- sector classification (for the Risk tab's concentration bars) ----------
# Disk-cached forever once known (cache/sectors.json — edit it to correct a
# name); a failed lookup is NOT cached, so it retries next build.
SECTOR_CACHE_PATH = os.path.join(HERE, "cache", "sectors.json")
_sector_lock = threading.Lock()
_sectors = None


def _fetch_sector_us(sym):
    rows = fmp_get("profile", symbol=sym) or []
    row = rows[0] if isinstance(rows, list) and rows else (rows if isinstance(rows, dict) else {})
    return (row or {}).get("sector") or None


def _fetch_sector_yahoo(ysym):
    """Yahoo's profile for a Yahoo symbol, the feed's profile on the same
    symbol as the fallback. Either can be empty for small names."""
    if not ysym:
        return None
    if _yahoo["session"] or _yahoo_auth():
        try:
            r = _yahoo["session"].get(
                f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ysym}",
                params={"modules": "assetProfile", "crumb": _yahoo["crumb"]}, timeout=15)
            res = (r.json().get("quoteSummary", {}).get("result") or [None])[0] or {}
            sec = (res.get("assetProfile") or {}).get("sector")
            if sec:
                return sec
        except Exception:  # noqa: BLE001
            pass
    return _fetch_sector_us(ysym)


def sector_of(key, fetch):
    """Memoised sector lookup: cache/sectors.json first, else fetch() once."""
    global _sectors
    with _sector_lock:
        if _sectors is None:
            try:
                with open(SECTOR_CACHE_PATH) as fh:
                    _sectors = json.load(fh)
            except (OSError, ValueError):
                _sectors = {}
        if key in _sectors:
            return _sectors[key]
    try:
        val = fetch()
    except Exception:  # noqa: BLE001
        val = None
    if not val:
        return None
    with _sector_lock:
        _sectors[key] = val
        try:
            with open(SECTOR_CACHE_PATH, "w") as fh:
                json.dump(_sectors, fh, indent=1, sort_keys=True)
        except OSError:
            pass
    return val


# ---- portfolio risk panel (beta / vol / drawdown / correlation, all books) ---
RISK_TTL = 1800


def build_risk():
    """Risk analytics across the books: the broker account(s) on Desk · Home
    (equity plus futures at notional, the margin cushion where the broker
    reports one) against the home market's index, and the US book against the
    S&P 500. Benchmarks keyless from Yahoo; home daily histories reuse the
    per-day disk cache the ticker pages fill."""
    m = _market()
    home_bench = m.META["benchmark"] if m else "^GSPC"
    home_label = m.META["benchmark_label"] if m else "S&P 500"
    if (os.getenv("RISK_BENCHMARK") or "").strip():           # the reader's own index, from the Risk screen
        home_bench = os.getenv("RISK_BENCHMARK").strip()
        home_label = (os.getenv("RISK_BENCHMARK_LABEL") or "").strip() or home_bench
    home_cur = m.META["symbol"] if m else "$"
    home_exch = m.META["exchanges"][0] if m else ""
    home_region = m.META["id"] if m else "home"
    benches = {}
    for sym in {home_bench, "^GSPC"}:
        h = risk.yahoo_history(sym)
        if h:
            benches[sym] = h
    books = []
    stale_used = False
    prev = load_last_snapshot()
    prev_accounts = (prev or {}).get("data", {}).get("accounts", {})
    accounts_iter = list(clients.items()) or [(n, None) for n in prev_accounts]
    for account, cli in accounts_iter:
        label = ACCOUNT_LABELS.get(account, account)
        equity, futures, funds = [], [], {}
        if cli is not None:
            try:
                equity, futures, funds = _reads(cli)
            except Exception:  # noqa: BLE001
                pass
        if not equity and not futures:
            # dead session: the last saved broker book still prices the risk
            # view (histories come from the disk cache, benchmarks from Yahoo)
            pa = prev_accounts.get(account)
            if not pa:
                continue
            equity = pa.get("equity") or []
            futures = pa.get("futures") or []
            funds = pa.get("funds") or {}
            label = pa.get("label") or label
            stale_used = True
        if not equity and not futures:
            continue
        pos = {}
        for e in equity:
            if not e.get("value") or not e.get("code"):
                continue
            p = pos.setdefault(e["code"], {"code": e["code"], "exposure": 0.0, "kinds": [],
                                           "exch": e.get("exch") or home_exch,
                                           "name": e.get("name") or "", "ysym": e.get("ysym") or ""})
            p["exposure"] += e["value"]
            if "EQ" not in p["kinds"]:
                p["kinds"].append("EQ")
        for f in futures:
            code = f.get("underlying")
            if not code or not f.get("notional"):
                continue
            sign = 1 if (f.get("side") or "Buy").lower() == "buy" else -1
            r = _resolve(code)
            p = pos.setdefault(code, {"code": code, "exposure": 0.0, "kinds": [],
                                      "exch": r.get("exch") or home_exch,
                                      "name": r.get("name") or "", "ysym": r.get("ysym") or ""})
            p["exposure"] += sign * f["notional"]
            if "FUT" not in p["kinds"]:
                p["kinds"].append("FUT")
        positions = []
        for p in pos.values():
            hist = _daily_history_home(p["code"], p["exch"])   # newest-first
            r = _resolve(p["code"], p["exch"])
            ysym = p.get("ysym") or r.get("ysym") or ""
            positions.append({"code": p["code"], "exposure": p["exposure"], "kinds": p["kinds"],
                              "exch": p["exch"], "name": p.get("name") or r.get("name") or "",
                              "sector": sector_of(f"{home_region.upper()}:{p['code']}",
                                                  lambda s=ysym: _fetch_sector_yahoo(s)),
                              "series": [(row["date"], row["price"]) for row in reversed(hist)]})
        eq_value = sum(e["value"] for e in equity if e["value"] is not None)
        cash = funds.get("cash") or 0
        limit_total = funds.get("fno_limit_total")
        blocked = funds.get("fno_blocked") or 0
        cur_code = funds.get("currency") or (equity[0].get("currency") if equity else "")
        books.append({
            "key": account, "label": label,
            "currency": home_cur if (not cur_code or (m and cur_code == m.META["currency"])) else cur_code + " ",
            "bench": home_bench, "bench_label": home_label, "region": home_region,
            "nav": eq_value + cash, "cash": cash, "positions": positions,
            "margin": ({**funds, "util_pct": (blocked / limit_total * 100) if limit_total else None}
                       if limit_total else None),
        })
    try:
        usb = load_book()
        frm = (datetime.now() - timedelta(days=500)).strftime("%Y-%m-%d")
        positions = []
        for pn in us_book_positions():
            sym = pn["symbol"]
            with _watch_lock:
                q = WATCH_US.get(sym)
            q = q or fetch_us_quote(sym)
            rows = fmp_get("historical-price-eod/light", symbol=sym, **{"from": frm}) or []
            series = sorted(((r.get("date"),
                              _num(r.get("price") if r.get("price") is not None else r.get("close")))
                             for r in rows), key=lambda x: x[0] or "")
            series = [(d, v) for d, v in series if d and v]
            price = (q["ltp"] if q else None) or (series[-1][1] if series else None)
            if price is None:
                continue
            positions.append({"code": sym, "name": pn.get("name") or "",
                              "kinds": ["EQ"], "exposure": price * pn["shares"],
                              "sector": sector_of("US:" + sym,
                                                  lambda s=sym: _fetch_sector_us(s)),
                              "series": series})
        cash = sum(float(c.get("amount") or 0) for c in usb.get("cash", [])
                   if str(c.get("currency", "")).upper() == "USD")
        if positions:
            books.append({"key": "us_book", "label": "Desk · Book, US names", "currency": "$",
                          "bench": "^GSPC", "bench_label": "S&P 500", "region": "us",
                          "nav": cash + sum(p["exposure"] for p in positions),
                          "cash": cash, "positions": positions, "margin": None,
                          "note": "the US names kept by hand on Desk · Book; cash account, no margin"})
    except (OSError, ValueError):
        pass
    data = risk.build(books, benches)
    data["session_dead"] = broker_health["dead"]
    data["stale"] = ({"broker_as_of": datetime.fromtimestamp(prev["at"]).strftime("%a %d %b, %H:%M")}
                     if (stale_used and prev) else None)
    return data


# ---- 13D/G activist feed (EDGAR full-text search; see activist.py) -----------
ACT_TTL = 12 * 3600


def build_activist():
    """13D/G filings on our names + by the tracked funds + a recent-13D
    firehose. All from EDGAR's full-text search (the live SCHEDULE 13D/G
    root forms — the old SC 13D root froze Dec 2024)."""
    our = {}
    for n in load_watchlist_us():
        our[n["code"]] = "watch"
    for p in us_book_positions():
        our[p["symbol"]] = "held"
    return activist.build(our, desk_lists.effective("funds"))


# ---- US options flow (CBOE delayed chains; the options-tape method) ----------
FLOW_TTL = 3600


def build_flow():
    """Options positioning across the US book + watchlist. The daily snapshot
    lands on disk inside options_us.build, so day-over-day OI builds appear
    from the second day a name is covered."""
    held = {p["symbol"] for p in us_book_positions()}
    syms = sorted(held | {n["code"] for n in load_watchlist_us()})
    return options_us.build(syms, held)


# ---- short interest + daily short-volume ratio (FINRA, free) -----------------
SHORT_TTL = 12 * 3600
_float_cache = {}


def _float_shares(sym):
    """Float via FMP shares-float (audited working on Starter); day-cached."""
    hit = _float_cache.get(sym)
    if hit and time.time() - hit[0] < 24 * 3600:
        return hit[1]
    rows = fmp_get("shares-float", symbol=sym)
    f = _num((rows[0] or {}).get("floatShares")) if isinstance(rows, list) and rows else None
    if f:
        _float_cache[sym] = (time.time(), f)
    return f


def build_short():
    held = {p["symbol"] for p in us_book_positions()}
    syms = sorted(held | {n["code"] for n in load_watchlist_us()})
    return shortint.build(syms, held, float_lookup=_float_shares)


# ---- US market pulse (movers + sector heat; audited working on Starter) ------
def _pulse_free():
    """The pulse without a key: Nasdaq's public screener hands out every large and mega cap
    with today's move, volume and sector in one answer. Gainers, losers and the most active by
    dollar traded come from that list, and the sector snapshot is the cap-weighted move of each
    sector today. Small caps stay out on purpose: the free list is the liquid market."""
    from calendar_desk import _NASDAQ_UA
    try:
        r = requests.get("https://api.nasdaq.com/api/screener/stocks",
                         params={"tableonly": "false", "limit": 1500, "marketcap": "mega|large", "download": "true"},
                         headers=_NASDAQ_UA, timeout=30)
        d = r.json().get("data") or {}
        rows = d.get("rows") or (d.get("table") or {}).get("rows") or []
    except Exception:  # noqa: BLE001
        rows = []
    names = []
    for x in rows:
        try:
            price = float(str(x.get("lastsale", "")).replace("$", "").replace(",", ""))
            chg = float(str(x.get("pctchange", "")).replace("%", "").replace(",", ""))
            vol = float(str(x.get("volume", "0")).replace(",", "") or 0)
            cap = float(str(x.get("marketCap", "0")).replace(",", "") or 0)
        except ValueError:
            continue
        nm = re.sub(r"\s+(Common Stock|Class [A-C] .*|Ordinary Shares.*|Depositary Shares.*)$", "", str(x.get("name") or ""))
        names.append({"symbol": x.get("symbol"), "name": nm, "price": price, "chg_pct": chg,
                      "dollar": price * vol, "cap": cap, "sector": x.get("sector") or ""})
    if not names:
        return {"gainers": [], "losers": [], "actives": [], "sectors": [], "sector_date": None,
                "note": "the market pulse could not be read from the free record just now; it is tried again in a few minutes", "_ttl": 300,
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}
    slim = lambda r: {"symbol": r["symbol"], "name": r["name"], "price": r["price"], "chg_pct": r["chg_pct"]}
    by_chg = sorted(names, key=lambda r: r["chg_pct"])
    actives = sorted(names, key=lambda r: -r["dollar"])[:10]
    agg = {}
    for r in names:
        if r["sector"] and r["cap"] and r["sector"] != "Miscellaneous":
            a = agg.setdefault(r["sector"], [0.0, 0.0])
            a[0] += r["chg_pct"] * r["cap"]
            a[1] += r["cap"]
    sectors = sorted(({"sector": k, "chg": v[0] / v[1]} for k, v in agg.items() if v[1]), key=lambda x: -x["chg"])
    return {"gainers": [slim(r) for r in by_chg[::-1][:10]], "losers": [slim(r) for r in by_chg[:10]],
            "actives": [slim(r) for r in actives], "sectors": sectors, "sector_date": datetime.now().strftime("%Y-%m-%d"),
            "note": "the free record: large and mega caps, movers by today's change, most active by dollars traded, sectors cap-weighted · refreshes every 15 min",
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}


def build_pulse():
    if not os.getenv("FMP_API_KEY", "").strip():
        return _pulse_free()
    with ThreadPoolExecutor(max_workers=4) as ex:
        g = ex.submit(fmp_get, "biggest-gainers")
        l = ex.submit(fmp_get, "biggest-losers")
        a = ex.submit(fmp_get, "most-actives")
        gainers, losers, actives = g.result() or [], l.result() or [], a.result() or []

    def _trim(rows):
        out = []
        for r in rows[:10]:
            out.append({"symbol": r.get("symbol"), "name": r.get("name"),
                        "price": _num(r.get("price")),
                        "chg_pct": _num(r.get("changesPercentage"))})
        return out

    # sector snapshot: walk back to the last day the market actually printed
    sectors, sec_date = [], None
    for back in range(1, 6):
        d = (datetime.now(timezone.utc) - timedelta(days=back)).strftime("%Y-%m-%d")
        rows = fmp_get("sector-performance-snapshot", date=d) or []
        nyse = [r for r in rows if r.get("exchange") == "NYSE"] or rows
        if nyse:
            seen = {}
            for r in nyse:
                seen.setdefault(r.get("sector"), _num(r.get("averageChange")))
            sectors = sorted(({"sector": k, "chg": v} for k, v in seen.items()
                              if k and v is not None), key=lambda x: -x["chg"])
            sec_date = d
            break
    return {"gainers": _trim(gainers), "losers": _trim(losers),
            "actives": _trim(actives), "sectors": sectors, "sector_date": sec_date,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}


# ---- Capitol trades (FMP senate/house disclosures — audited working) ---------
def _norm_congress(rows, chamber):
    out = []
    for r in rows or []:
        sym = (r.get("symbol") or "").strip().upper()
        out.append({
            "chamber": chamber,
            "symbol": sym,
            "name": f"{r.get('firstName') or ''} {r.get('lastName') or ''}".strip()
                    or (r.get("office") or ""),
            "district": r.get("district") or "",
            "owner": r.get("owner") or "",
            "asset": r.get("assetDescription") or "",
            "asset_type": r.get("assetType") or "",
            "type": r.get("type") or "",
            "amount": r.get("amount") or "",
            "tx": r.get("transactionDate") or "",
            "disclosed": r.get("disclosureDate") or "",
            "link": r.get("link") or "",
        })
    return out


def build_capitol():
    """Congress trading: the disclosure firehose plus every filing that touches
    a name on the book or watchlist. Read-only public PTR data via FMP."""
    ours = set()
    held = {p["symbol"] for p in us_book_positions()}
    ours |= held
    ours |= {n["code"] for n in load_watchlist_us()}

    try:
        tracked_members = desk_lists.effective("members")
    except (OSError, ValueError):
        tracked_members = []
    if not os.getenv("FMP_API_KEY", "").strip():
        return house_ptr.build(sorted(ours), tracked_members, held)

    jobs = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        latest_f = {
            "senate": [ex.submit(fmp_get, "senate-latest", page=p, limit=100) for p in (0, 1)],
            "house": [ex.submit(fmp_get, "house-latest", page=p, limit=100) for p in (0, 1)],
        }
        for sym in sorted(ours):
            jobs[sym] = (ex.submit(fmp_get, "senate-trades", symbol=sym),
                         ex.submit(fmp_get, "house-trades", symbol=sym))
        member_f = [(m, ex.submit(fmp_get, f"{m.get('chamber', 'house')}-trades-by-name",
                                  name=m["name"], page=0, limit=100))
                    for m in tracked_members]
        djt_f = ex.submit(fmp_get, "insider-trading/search", symbol="DJT", limit=15)
        flow = []
        for chamber, futs in latest_f.items():
            for f in futs:
                flow.extend(_norm_congress(f.result(), chamber))
        mine = []
        for sym, (sf, hf) in jobs.items():
            mine.extend(_norm_congress(sf.result(), "senate"))
            mine.extend(_norm_congress(hf.result(), "house"))
        members = []
        for m, fut in member_f:
            rows = _norm_congress(fut.result(), m.get("chamber", "house"))
            rows.sort(key=lambda r: r["tx"] or "", reverse=True)
            members.append({"label": m.get("label") or m["name"],
                            "chamber": m.get("chamber", "house"),
                            "count": len(rows), "rows": rows[:100]})

    flow.sort(key=lambda r: r["disclosed"] or "", reverse=True)
    # de-dup our-names rows and keep the recent year of activity
    seen, ours_rows = set(), []
    for r in sorted(mine, key=lambda r: r["tx"] or "", reverse=True):
        k = (r["chamber"], r["symbol"], r["name"], r["tx"], r["amount"], r["type"])
        if k in seen:
            continue
        seen.add(k)
        ours_rows.append(r)
    djt = [{"filed": r.get("filingDate"), "name": r.get("reportingName"),
            "type": r.get("transactionType"),
            "shares": _num(r.get("securitiesTransacted")),
            "price": _num(r.get("price"))} for r in (djt_f.result() or [])]
    return {"ours": ours_rows[:80], "flow": flow[:200], "members": members,
            "djt": djt, "held": sorted(held), "tracked": len(ours),
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}


DISKLESS = {"snap", "tape", "book"}   # position data: never serve a restart a stale book


_building = set()
_building_lock = threading.Lock()


def _store(kind, data):
    _cache[kind] = (time.time(), data)
    if kind not in DISKLESS:
        try:
            with open(os.path.join(HIST_CACHE_DIR, f"api_{kind}.json"), "w") as fh:
                json.dump({"at": time.time(), "data": data}, fh)
        except OSError:
            pass


def _rebuild(kind, builder):
    try:
        data = builder()
        if data is not None:
            _store(kind, data)
    except Exception as exc:  # noqa: BLE001 - a failed rebuild keeps the old copy, and the log says so
        print(f"  {kind}: rebuild failed: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
    finally:
        with _building_lock:
            _building.discard(kind)


def _spawn(kind, builder):
    """Start one background rebuild of a kind; no-op if one is running."""
    with _building_lock:
        if kind in _building:
            return False
        _building.add(kind)
    threading.Thread(target=_rebuild, args=(kind, builder), daemon=True).start()
    return True


def _ttl_of(data, ttl):
    """A build that could not reach part of its feed asks to be retried sooner
    (a "_ttl" in the answer); otherwise the kind's own TTL."""
    try:
        return min(ttl, float(data.get("_ttl") or ttl)) if isinstance(data, dict) else ttl
    except (TypeError, ValueError):
        return ttl


def _cached(kind, ttl, builder):
    """Serve what we have and refresh behind the page. Once a kind has been
    built once (or has a disk copy from an earlier run), a click never waits
    for a rebuild: the stale copy goes out at once and the rebuild runs in a
    thread, so the next click gets the fresh one. His complaint: Commodities
    and Chain took minutes on every visit because the old version rebuilt
    inline whenever the TTL had passed. Only the very first build blocks."""
    with _locks[kind]:
        stamp, data = _cache[kind]
        if data is None and kind not in DISKLESS:
            try:
                with open(os.path.join(HIST_CACHE_DIR, f"api_{kind}.json")) as fh:
                    c = json.load(fh)
                _cache[kind] = (c["at"], c["data"])
                stamp, data = _cache[kind]
            except (OSError, ValueError, KeyError):
                pass
        if data is not None:
            if time.time() - stamp >= _ttl_of(data, ttl):
                _spawn(kind, builder)
            return data
    _spawn(kind, builder)
    for _ in range(1200):            # first ever build: wait for it, up to 10 min
        data = _cache[kind][1]
        if data is not None:
            return data
        with _building_lock:
            if kind not in _building:
                break
        time.sleep(0.5)
    return _cache[kind][1] if _cache[kind][1] is not None else {}


# ---- Settings: the broker connected from the page, not the terminal ---------
def _start_stream(cli):
    """Live ticks for Watch · Home, where the broker's file serves them."""
    mod = ADAPTER["mod"]
    if mod is None or not hasattr(mod, "stream"):
        return

    def _stream_sink(code, q):
        with _watch_lock:
            WATCH[code] = q
    try:
        mod.stream(cli, load_watchlist, _stream_sink, home_market_open)
    except Exception as exc:  # noqa: BLE001
        print(f"  live ticks not started: {exc}")


def _forget_screens(disk=True):
    """After a broker connects or leaves, every screen that reads the broker is stale at once:
    the copy in memory keeps serving while it rebuilds, and the copy on disk goes, so a read
    that finds nothing in memory does not bring back the pre-connect answer for its TTL.
    At boot the broker is the same one as before the restart, so the disk copies stay
    (`disk=False`): removing them there made every restart rebuild Commodities and Chain
    from nothing and spent the free feed's budget on it."""
    for k in ("snap", "risk", "tape", "results_home", "macro", "econcal", "commods", "chain"):
        _cache[k] = (0.0, _cache.get(k, (0.0, None))[1])
        if not disk:
            continue
        try:
            os.remove(os.path.join(HIST_CACHE_DIR, f"api_{k}.json"))
        except OSError:
            pass


def connect_broker_now(bid=None, at_boot=False):
    """Connect one broker the reader chose on Settings (the home one when none is named), at
    boot or from the page, with no restart. Returns plain words for the page."""
    ids = brokers.active_ids()
    bid = (bid or "").strip().lower() or (ids[0] if ids else "")
    # the modules of every connected broker are loaded first, so the home adapter can be chosen
    for other in ids:
        if other not in MODS:
            MODS[other] = brokers.load(other)
    for gone in [k for k in list(MODS) if k not in ids]:
        MODS.pop(gone, None)
        clients.pop(gone, None)
        ACCOUNT_LABELS.pop(gone, None)
    _pick_adapter()
    if not bid:
        clients.clear()
        ACCOUNT_LABELS.clear()
        broker_health["dead"] = True
        _forget_screens(disk=not at_boot)
        return {"ok": False, "error": "No broker chosen."}
    if bid not in ids:
        return {"ok": False, "error": "That broker is not on this desk."}
    mod = MODS[bid]
    if not brokers.configured(bid):
        return {"ok": False, "error": "Save the broker's keys first."}
    cfg = brokers.config(bid)
    token = brokers.read_token(bid) if mod.META["daily_login"] else None
    if mod.META["daily_login"] and not token:
        broker_health["dead"] = not clients
        return {"ok": False, "need_token": True, "error": "No login for today yet. Open the broker login below and paste what it hands back."}
    try:
        cli = mod.connect(cfg, token)
    except brokers.BrokerError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "Could not connect: " + str(exc)[:160]}
    if cli is None:
        return {"ok": False, "need_token": True, "error": "The broker did not accept today's login. It may be from an earlier day, or pasted with a character missing."}
    clients[bid] = cli
    try:
        ACCOUNT_LABELS[bid] = mod.label(cli)
    except Exception:  # noqa: BLE001
        ACCOUNT_LABELS[bid] = "account"
    broker_health["dead"] = False
    _forget_screens(disk=not at_boot)
    if bid == ADAPTER["id"]:
        _start_stream(cli)
    try:
        n = len(mod.equity(cli))
    except Exception:  # noqa: BLE001
        n = None
    return {"ok": True, "label": ACCOUNT_LABELS[bid], "positions": n, "broker": bid}


def connect_all_brokers():
    """Every connected broker, at boot; the last report per broker."""
    out = {}
    for bid in brokers.active_ids():
        out[bid] = connect_broker_now(bid, at_boot=True)
    if not out:
        connect_broker_now("", at_boot=True)
    return out


def disconnect_broker(bid):
    """A broker off the desk: its id leaves BROKERS, its client and its token go."""
    ids = [b for b in brokers.active_ids() if b != bid]
    desk_settings.write_env({"BROKERS": ",".join(ids), "BROKER": ids[0] if ids else ""})
    clients.pop(bid, None)
    MODS.pop(bid, None)
    ACCOUNT_LABELS.pop(bid, None)
    brokers.clear_token(bid)
    _pick_adapter()
    broker_health["dead"] = not clients
    _forget_screens()


def _masked(v):
    return desk_settings.masked(v)


def broker_state(bid=None):
    bid = (bid or ADAPTER["id"] or brokers.active_id() or "")      # the home broker is the one in the home market, not the first saved
    mod = brokers.load(bid) if bid else None
    st = {"id": bid, "connected": bid in clients, "account": ACCOUNT_LABELS.get(bid, ""),
          "configured": brokers.configured(bid) if bid else False, "home": bid == ADAPTER["id"]}
    if mod:
        m = mod.META
        cfg = brokers.config(bid)
        fields = []
        for f in m["fields"]:
            v = cfg.get(f["env"], "")
            fields.append({**f, "saved": ("on" if v.lower() in ("on", "1", "true", "yes") else "off") if f.get("switch") else _masked(v)})
        st.update({"label": m["label"], "where": m["where"], "daily_login": m["daily_login"], "how": m["how"],
                   "docs": m["docs"], "fields": fields, "token_hint": m.get("token_hint", ""),
                   "token_param": m.get("token_param", ""), "region": m.get("region", ""),
                   "desk": desk_of(m.get("region", ""))})
        if m["daily_login"]:
            st["token_today"] = brokers.read_token(bid) is not None
            st["login_url"] = mod.login_url(cfg) if (st["configured"] and hasattr(mod, "login_url")) else ""
    return st


def brokers_state():
    """Every broker the reader connected, the home one first."""
    return [broker_state(b) for b in brokers.active_ids()]


# ---------------------------------------------------------------- the sidebar
# Every screen, by key. A reader hides any of them with one click on the rail or in
# Settings, and that choice is kept in .env as SCREENS=chain:off,short:off. The US
# panels (the US book, the earnings ahead, the pulse, the insider tape) are part of
# Desk · Home for every reader since 2026-09-15.20; they were a screen of their own.
SCREENS = [
    ("home", "/", "Desk · Home"), ("book", "/book", "Desk · Book"),
    ("risk", "/risk", "Risk"), ("watch", "/watch", "Watch · Home"), ("watchus", "/watch?list=us", "Watch · US"),
    ("global", "/watch?list=global", "Global"), ("funds", "/funds", "Funds"), ("flow", "/flow", "Flow"),
    ("short", "/short", "Short"), ("capitol", "/capitol", "Capitol"), ("macro", "/macro", "Macro"),
    ("calendar", "/calendar", "Calendar"),
    ("commods", "/commods", "Commodities"), ("chain", "/chain", "Chain"), ("notes", "/notes", "Notes"),
    ("settings", "/settings", "Settings"),
]
ALWAYS_SHOWN = {"home", "settings"}


def screen_choices():
    out = {}
    for part in (os.getenv("SCREENS", "") or desk_settings.read_env().get("SCREENS", "") or "").split(","):
        if ":" in part:
            k, v = part.strip().split(":", 1)
            if k in {s[0] for s in SCREENS}:
                out[k] = v.strip().lower() == "on"
    return out


def nav_state():
    hm = _market()
    hm_id = hm.META.get("id") if hm else None
    # a reader whose home is the US has the US list already (Watch · US carries the 52-week,
    # moving-average and market-cap columns); Watch · Home would be the same names with fewer
    # columns, so it steps aside and Settings can show it again
    default_hidden = {"watch"} if hm_id == "us" else set()
    choices = screen_choices()
    hidden = [k for k, _, _ in SCREENS
              if k not in ALWAYS_SHOWN and not choices.get(k, k not in default_hidden)]
    try:
        journal_pending = len(desk_notes.journal_pending()) if desk_notes.journal_mode() == "ask" else 0
    except Exception:  # noqa: BLE001
        journal_pending = 0
    try:
        plugin_screens = desk_plugins.screens()
    except Exception:  # noqa: BLE001
        plugin_screens = []
    return {"hidden": hidden, "default_hidden": sorted(default_hidden), "choices": choices, "journal_pending": journal_pending,
            "plugin_screens": plugin_screens,
            "home_market": hm_id,
            "screens": [{"key": k, "href": h, "label": l, "shown": k not in hidden, "fixed": k in ALWAYS_SHOWN} for k, h, l in SCREENS]}


def settings_state():
    st = desk_settings.current()
    st["broker"] = broker_state()
    st["connected"] = brokers_state()
    st["brokers"] = [{k: v for k, v in m.items() if k != "fields"} | {"fields": m["fields"]} for m in brokers.all_meta()]
    st["others"] = [{"name": n, "path": p} for n, p in brokers.OTHERS]
    st["market"] = _market_info()
    st["markets"] = [{"id": mm["id"], "label": mm["label"], "record": mm.get("record", "full"),
                      "currency": mm["currency"], "exchanges": mm["exchanges"], "benchmark_label": mm["benchmark_label"]}
                     for mm in markets.all_meta()]
    st["ai"]["providers"] = desk_ai.PROVIDERS
    st["ai"]["formats"] = desk_ai.FORMATS
    st["desk"] = {"port": PORT, "folder": HERE, "version": updater.local_version(),
                  "autostart": desk_settings.autostart_status(),
                  "agent_url": f"http://localhost:{PORT}/agent",
                  "log": os.path.join(HERE, "logs", "desk-service.log"),
                  "building": sorted(_building), "home_broker": ADAPTER["id"], "clients": sorted(clients)}
    st["profile"] = desk_settings.load_profile()
    st["profile_choices"] = desk_settings.PROFILE_CHOICES
    st["files"] = desk_settings.data_files()
    st["nav"] = nav_state()
    return st


# ---------------------------------------------------------------- the Ask box
# What the Ask box reads for each screen, the same addresses the /agent page lists.
ASK_READS = {
    "/": ("Desk · Home", ["/api/snapshot", "/api/alerts", "/api/usbook", "/api/earnings", "/api/insiders"]),
    "/book": ("Desk · Book", ["/api/book"]),
    "/risk": ("Risk", ["/api/risk"]),
    "/watch": ("Watch", ["/api/watch?list={list}", "/api/results_home"]),
    "/funds": ("Funds", ["/api/funds"]),
    "/flow": ("Flow", ["/api/flow"]),
    "/short": ("Short", ["/api/short"]),
    "/capitol": ("Capitol", ["/api/capitol"]),
    "/calendar": ("Calendar", ["/api/calendar"]),
    "/macro": ("Macro", ["/api/macro", "/api/econcal", "/api/research/context?kind=macro"]),
    "/commods": ("Commodities", ["/api/commods", "/api/research/context?kind=commodity"]),
    "/chain": ("Chain", ["/api/chain"]),
    "/t": ("Ticker", ["/api/ticker?symbol={symbol}&region={region}", "/api/research/context?symbol={symbol}"]),
    "/notes": ("Notes", ["/api/notes", "/api/notes/graph"]),
    "/settings": ("Settings", []),
}
ASK_CAP = 90000   # characters of screen data sent with a question, at most


BULKY = {"full", "spark", "hist", "history", "candles", "intensity", "intensity_source", "pricing_power", "note", "also"}


def _slim(obj, drop=frozenset()):
    """The same numbers, made to fit one question: a price history of 400 points
    becomes its first and last few, a long sentence is cut at 160 characters,
    and on a second pass the descriptive keys in `drop` go entirely."""
    if isinstance(obj, dict):
        return {k: _slim(v, drop) for k, v in obj.items() if k not in drop}
    if isinstance(obj, list):
        if len(obj) > 40 and all(isinstance(x, (int, float, str, list, tuple)) and not isinstance(x, dict) for x in obj[:8]):
            return obj[:6] + [f"... {len(obj) - 12} more points ..."] + obj[-6:]
        return [_slim(x, drop) for x in obj[:400]]
    if isinstance(obj, str) and len(obj) > 160:
        return obj[:160] + "…"
    return obj


def ask_ready():
    s = desk_ai.settings()
    why = desk_ai.not_ready(s)
    doors = desk_plugins.doors()
    default_door = (os.getenv("AI_DOOR") or "").strip()
    if default_door and not any(d["name"] == default_door and d["ready"] for d in doors):
        default_door = ""
    return {"ready": why is None, "why": why, "provider": s["provider"],
            "label": desk_ai.PROVIDERS.get(s["provider"], {}).get("label", ""), "model": s["model"],
            "doors": doors, "default_door": default_door,
            "web": desk_ai.web_ready(s) is None if why is None else False,
            "web_why": desk_ai.web_ready(s) if why is None else "",
            # the names the box offers for the key on Settings: Anthropic's own list when that is the
            # provider; any other provider takes the name typed, as the provider's page spells it
            "models": desk_plugins.APPS["claude"]["models"] if s["provider"] == "anthropic" else []}


# The Ask box's conversations, kept on this desk (data/ask_threads.json, never the vault)
# so closing the box, changing screens or reloading does not lose them. The box shows the
# latest one on open; the reader starts a new one, picks an old one, or deletes any of them.
ASK_THREADS_PATH = os.path.join(DATA_DIR, "ask_threads.json")
ASK_THREADS_KEEP = 40
_ask_threads_lock = threading.Lock()


def _ask_threads_read():
    try:
        with open(ASK_THREADS_PATH) as fh:
            rows = json.load(fh).get("threads") or []
    except (OSError, ValueError):
        rows = []
    return [r for r in rows if isinstance(r, dict) and r.get("id")]


def _ask_threads_write(rows):
    rows = sorted(rows, key=lambda r: r.get("at", ""), reverse=True)[:ASK_THREADS_KEEP]
    tmp = ASK_THREADS_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"threads": rows}, fh)
    os.replace(tmp, ASK_THREADS_PATH)
    return rows


def ask_threads_list():
    return [{"id": r["id"], "title": r.get("title", ""), "screen": r.get("screen", ""), "at": r.get("at", ""),
             "n": len(r.get("msgs") or [])} for r in sorted(_ask_threads_read(), key=lambda r: r.get("at", ""), reverse=True)]


def ask_thread_get(tid):
    return next((r for r in _ask_threads_read() if r["id"] == tid), None)


def ask_thread_save(body):
    """The whole thread as the box holds it: id (new when empty), title, screen, msgs."""
    tid = re.sub(r"[^a-z0-9]", "", str(body.get("id", "")))[:24] or f"{int(time.time() * 1000):x}"
    msgs = [{"role": m.get("role"), "content": str(m.get("content", ""))[:20000], "model": str(m.get("model", ""))[:80],
             "read": [str(x)[:80] for x in (m.get("read") or [])][:20],
             "sources": [{"url": str(x.get("url", ""))[:400], "title": str(x.get("title", ""))[:200]} for x in (m.get("sources") or []) if isinstance(x, dict)][:20]}
            for m in (body.get("msgs") or []) if isinstance(m, dict) and m.get("role") in ("user", "assistant")][:200]
    row = {"id": tid, "title": str(body.get("title", ""))[:120], "screen": str(body.get("screen", ""))[:80],
           "at": datetime.now().strftime("%Y-%m-%d %H:%M"), "msgs": msgs}
    with _ask_threads_lock:
        rows = [r for r in _ask_threads_read() if r["id"] != tid]
        if msgs:
            rows.append(row)
        _ask_threads_write(rows)
    return row


def ask_thread_delete(tid):
    with _ask_threads_lock:
        rows = _ask_threads_read()
        if tid == "all":
            _ask_threads_write([])
            return True
        keep = [r for r in rows if r["id"] != tid]
        _ask_threads_write(keep)
        return len(keep) != len(rows)


def open_signin_window(app):
    """A terminal window on this computer running the app's own sign-in, which opens the reader's
    browser; the desk never sees the login. Returns words for the reader."""
    a = desk_plugins.APPS.get(app)
    if not a:
        return {"ok": False, "error": "no such app"}
    cmd = a["signin"]
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["osascript", "-e", 'tell application "Terminal" to activate',
                              "-e", f'tell application "Terminal" to do script "{cmd}"'])
        elif sys.platform.startswith("win"):
            subprocess.Popen(f'start "GreekSoup sign in" cmd /k {cmd}', shell=True)
        else:
            term = shutil.which("x-terminal-emulator") or shutil.which("gnome-terminal") or shutil.which("konsole") or shutil.which("xterm")
            if not term:
                return {"ok": False, "error": f"Open a terminal yourself and run: {cmd}"}
            subprocess.Popen([term, "-e", cmd] if "gnome" not in term else [term, "--", "bash", "-lc", cmd])
    except OSError as exc:
        return {"ok": False, "error": f"Could not open a terminal ({exc}). Open one yourself and run: {cmd}"}
    return {"ok": True, "text": f"A terminal window opened with {a['label']}. Its sign-in runs in your browser; when it says you are in, close that window and come back here."}


# What the whole desk holds, one line per screen, so SuperAnalyst knows where an answer
# lives when the screen the reader is on does not carry it. A question is routed to the
# screens its words point at, and the model may ask for more by name (a NEED line).
DESK_MAP = [
    ("/api/snapshot", "Desk · Home", "the broker book: holdings, open futures, cash, margin, day change", ("book", "holding", "position", "portfolio", "cash", "margin", "futures", "account", "own", "hold")),
    ("/api/usbook", "Desk · Home", "the US names on Desk · Book, priced", ("us book", "us names", "hand-kept")),
    ("/api/earnings", "Desk · Home", "the US earnings countdown", ("earnings", "results", "report", "quarter")),
    ("/api/insiders", "Desk · Home", "insider buying and cluster buys (Form 4)", ("insider", "form 4", "cluster", "director", "officer", "bought", "buying")),
    ("/api/book", "Desk · Book", "the hand-kept book: positions, cost, value, P&L by currency", ("book", "holding", "position", "portfolio", "p&l", "pnl", "cost", "weight", "own", "hold")),
    ("/api/risk", "Risk", "beta, volatility, drawdown, sector concentration, correlation, per book and per name", ("risk", "beta", "volatil", "drawdown", "concentrat", "correlat", "hedge", "exposure", "sector")),
    ("/api/watch?list=home", "Watch · Home", "the home-market watchlist, priced, with levels", ("watch", "watchlist", "level", "home market")),
    ("/api/watch?list=us", "Watch · US", "the US watchlist, priced", ("watch", "watchlist", "us list")),
    ("/api/watch?list=global", "Global", "the global watchlist, any exchange", ("global", "watchlist", "index", "indices")),
    ("/api/results_home", "Watch · Home", "upcoming results dates in the home market", ("results", "board meeting", "quarter")),
    ("/api/calendar", "Calendar", "results, dividend dates and landed filings on every name held or watched", ("calendar", "when", "date", "upcoming", "dividend", "ex-div", "filing", "10-k", "10-q", "8-k", "proxy", "results", "earnings", "event", "next")),
    ("/api/funds", "Funds", "the followed funds' 13F holdings and changes", ("fund", "13f", "hedge", "manager", "holder", "institution", "burry", "berkshire")),
    ("/api/flow", "Flow", "the options tape on US names: put/call, walls, expected move, unusual strikes", ("option", "put", "call", "strike", "expected move", "flow", "gamma", "open interest")),
    ("/api/short", "Short", "short interest and daily short volume", ("short", "squeeze", "borrow")),
    ("/api/capitol", "Capitol", "congressional trading disclosures on the names", ("congress", "senate", "house", "capitol", "politician", "pelosi", "ptr")),
    ("/api/macro", "Macro", "the macro cards: rates, inflation, growth, the home market's own", ("macro", "rate", "inflation", "cpi", "fed", "rbi", "gdp", "yield", "bond", "repo", "unemployment", "economy")),
    ("/api/econcal", "Macro", "the economic calendar ahead", ("calendar", "print", "fomc", "cpi", "payroll", "jobs")),
    ("/api/commods", "Commodities", "the commodity board and who is exposed to each", ("commodit", "oil", "crude", "gold", "silver", "copper", "gas", "rubber", "steel", "wheat", "coal", "metal")),
    ("/api/chain", "Chain", "the reader's value chains: who sells to whom, priced", ("chain", "supplier", "customer", "upstream", "downstream", "value chain", "supply")),
    ("/api/notes", "Notes", "the research vault: every note, filtered", ("note", "vault", "wrote", "research", "thesis", "journal", "task", "document", "file", "project")),
    ("/api/research/tasks", "Notes", "what is due: results dates, follow-ups, the reader's own lines", ("task", "due", "todo", "follow")),
]


def _desk_map_text():
    return "\n".join(f"{u:28s} {lab:14s} {what}" for u, lab, what in ((m[0], m[1], m[2]) for m in DESK_MAP))


def _known_symbols():
    """Every symbol the desk holds or watches, so a bare AAPL in a question is recognised."""
    syms = set()
    try:
        syms |= {str(p.get("symbol") or "").upper() for p in load_book().get("positions", [])}
        for n in load_watchlist() + load_watchlist_us() + load_watchlist_global():
            syms.add(str(n.get("code") or "").upper())
        snap = load_last_snapshot() or {}
        accounts = (snap.get("data") or {}).get("accounts") or {}
        for acct in (accounts.values() if isinstance(accounts, dict) else accounts):
            syms |= {str(e.get("code") or "").upper() for e in acct.get("equity") or []}
    except Exception:  # noqa: BLE001
        pass
    syms.discard("")
    return syms


def ask_route(question, page, fill):
    """Which other screens a question points at: the names it mentions get their ticker page
    and the reader's notes on them; the words it uses get the screens whose subject they are."""
    q = (question or "").lower()
    urls = []
    known = _known_symbols()
    mentioned = []
    for tok in re.findall(r"\$?([A-Z][A-Z0-9]{0,9}(?:[.\-][A-Z0-9]{1,6})?)", question or ""):
        if (tok in known or ("$" + tok) in (question or "")) and tok not in mentioned and tok != fill.get("symbol"):
            mentioned.append(tok)
    for sym in mentioned[:3]:
        region = "home" if "." in sym and not sym.endswith((".US",)) else "us"
        urls.append(f"/api/ticker?symbol={sym}&region={region}")
        urls.append(f"/api/research/context?symbol={sym}")
    _, own = ASK_READS.get(page, ("", []))
    own_bases = {u.split("?")[0] for u in own}
    scored = []
    for url, lab, what, words in DESK_MAP:
        if url.split("?")[0] in own_bases or url in urls:
            continue
        hits = sum(1 for w in words if w in q)
        if hits:
            scored.append((hits, url))
    scored.sort(key=lambda x: -x[0])
    urls += [u for _, u in scored[:4]]
    return urls, mentioned


def ask_fetch(urls, budget, extra=False):
    """Read the desk's own addresses as text for the model, inside a character budget."""
    parts, used = [], []
    for url in urls:
        try:
            r = requests.get(f"http://127.0.0.1:{PORT}{url}", timeout=90)
            data = r.json()
        except Exception as exc:  # noqa: BLE001
            parts.append(f"{url}: could not be read ({type(exc).__name__})")
            continue
        if url.startswith("/api/research/context"):
            text = json.dumps(data, separators=(",", ":"), default=str, ensure_ascii=False)
        else:
            text = json.dumps(_slim(data, BULKY if extra else frozenset()), separators=(",", ":"), default=str)
        if len(text) > budget and not url.startswith("/api/research/context"):
            text = json.dumps(_slim(data, BULKY), separators=(",", ":"), default=str)
        if len(text) > budget:
            text = text[:max(budget, 0)] + " ...(cut here: the screen holds more than fits in one question)"
        budget -= len(text)
        parts.append(f"{url}\n{text}")
        used.append(url.split("?")[0])
        if budget <= 0:
            break
    return parts, used, budget


def ask_more(answer, already):
    """A NEED line in the answer names addresses from the desk map the model wants next:
    the ones it may have are fetched once and the question is asked again with them."""
    m = re.match(r"^\s*NEED:\s*(.+?)\s*$", (answer or "").strip(), re.S)
    if not m or "\n" in m.group(1).strip():
        return []
    allowed = {u.split("?")[0] for u, *_ in DESK_MAP} | {"/api/ticker", "/api/research/context", "/api/notes/get", "/api/research/timeline", "/api/research/status"}
    want = []
    for tok in re.split(r"[,\s]+", m.group(1)):
        tok = tok.strip().strip(".;")
        if tok.startswith("/api/") and tok.split("?")[0] in allowed and tok not in already and re.fullmatch(r"[A-Za-z0-9/?&=._%\-^]+", tok):
            want.append(tok)
    return want[:5]


def ask_context(page, query, question=""):
    """The screen's own numbers first, then the screens the question points at, read from the
    desk's own addresses, as text the model can read."""
    page = page if page in ASK_READS else "/"
    label, reads = ASK_READS[page]
    q = {k: re.sub(r"[^A-Za-z0-9._&=-]", "", str(v))[:40] for k, v in (query or {}).items() if isinstance(v, str)}
    fill = {"list": q.get("list") or "home", "symbol": q.get("symbol") or "", "region": q.get("region") or "us"}
    if page == "/watch" and fill["list"] != "home":
        label = {"us": "Watch · US", "global": "Global"}.get(fill["list"], "Watch")
    if page == "/t":
        label = "Ticker " + fill["symbol"]
    own = [ep.format(**fill) for ep in reads if not (page == "/t" and not fill["symbol"])]
    parts, used, budget = ask_fetch(own, ASK_CAP)
    routed, _ = ask_route(question, page, fill)
    if routed and budget > 4000:
        more, used2, budget = ask_fetch(routed, budget, extra=True)
        parts += more
        used += used2
    return label, "\n\n".join(parts) if parts else "(this screen has no numbers of its own)", used


AGENT_PAGE = """GreekSoup: the one-person equity research desk. This page is for an AI agent.

The desk runs on this computer at http://localhost:{port}/ and answers plain JSON at the
addresses below. Everything is read-only: nothing here places an order or changes an account.
Every figure names its source on the screen it came from; quote the source when you use a figure.

WHAT THE READER SEES (pages)             WHAT YOU CAN READ (JSON)
/            Desk - Home, the broker book  /api/snapshot   holdings, open futures, cash, margin
             and, below it, the US panels    /api/usbook     the hand-kept US positions, priced
/book        Desk - Book, kept by hand      /api/book       positions and cash by currency
/risk        Risk                           /api/risk       concentration, sector, beta, drawdown
/watch       Watch - Home                   /api/watch?list=home  quotes for the home watch grid
/watch?list=us      Watch - US              /api/watch?list=us    quotes for the US watch grid
/watch?list=global  Global                  /api/watch?list=global
                                            /api/results_home     upcoming results in the home market
/funds       Funds (13F)                    /api/funds      the followed funds' latest 13F holdings
/flow        Flow                           /api/flow       13D/G activist and large-holder filings
/short       Short                          /api/short      short interest
/capitol     Capitol                        /api/capitol    congressional trading disclosures
/macro       Macro                          /api/macro      the macro cards;  /api/econcal  the calendar
/commods     Commodities                    /api/commods    the commodity board and its exposure map
/chain       Chain                          /api/chain      the reader's value chains, priced; starters they have not put away
             A chain is a file in data/research/chains/<id>.json: title, region (us, home, global),
             layers upstream to downstream (name, sells, buys_from, sells_to, names with code,
             label, region, status, receipt, note, source) and edges (from, to, what, receipt,
             source). Receipts: DISCLOSED in a filing, ON RECORD, REPORTED. Write one only when
             the reader asks; the desk reads the folder on the next visit.
/notes       Notes, the research vault      /api/notes?symbol=&project=&kind=&period=&about=&type=&q=   the notes, filtered
                                            /api/notes/get?id=   one note with its body
                                            /api/notes/graph?symbol=   what connects to what
                                            /api/research/file?path=files/AAPL/x.pdf   a file the reader brought in
                                            /api/research/text?path=files/AAPL/x.pdf   the text the desk read out of it
                                            /api/research/context?symbol=AAPL   the reader's notes and files on a subject, as text
                                            /api/research/status?symbol=AAPL    where the name stands: watchlist, researching, thesis built, invested, exited
                                            /api/research/timeline?symbol=AAPL  everything about the name by period and date
                                            /api/research/tasks?symbol=         the reader's tasks (tasks.md, checkboxes in notes, results dates)
                                            /api/research/block?spec=chart+AAPL+1y   the data behind a live block in a note
             A note may carry live blocks: a fenced code block whose language is desk, one
             block per fence, e.g. ```desk / chart AAPL 1y / ```. The desk draws them on the
             note's page; an editor shows the fence as code. The blocks:
               quote SYM [SYM ...]  ·  chart SYM [1m|3m|6m|1y|2y|5y]  ·  watch SYM ... | watch project "Title"
               commodity NAME  ·  status SYM  ·  notes SYM [N]  ·  tasks [SYM]  ·  timeline SYM  ·  book
             A note that is mostly blocks is a dashboard.
                                            /api/research/journal               the journal: the moments the desk saw, and the reader's whys
             The vault is data/research: notes/ holds one Markdown file per note, files/ holds
             what the reader brought in (annual reports, models, screenshots), one folder per
             subject. A note's front matter card: title, kind (stock, commodity, sector, macro,
             general: what it is about), type (general, news, insight, concall, meeting, risk,
             answer, document, model, clipping, decision, exit, project: what sort of note),
             symbols (the listings), about (the commodity, sector or theme when the kind is not
             stock), period (the quarter or year researched, Q2 FY26 style), file (an attached
             file, files/<subject>/<name>), project, tags. A document is a note with a file
             attached. You may read and write those files directly; the desk re-reads the folder
             within seconds. $AAPL in a body names a listing, [[Title]] links to another note,
             a note of type project groups names and notes. Write a note only when the reader
             asks for one; nothing here is saved on its own.
/t?symbol=AAPL   a ticker page              /api/ticker?symbol=AAPL   chart, quote, ratios, insiders
/t?symbol=X&region=home  a home-market name /api/ticker?symbol=X&region=home  (broker code or exchange symbol)
                                            /api/fin?symbol=AAPL      statements, estimates, peers (needs the data key)
                                            /api/earnings   the US earnings countdown
                                            /api/insiders   the insider tape
                                            /api/alerts     the alerts that fired
                                            /api/search?q=apple&list=us   symbol search
/settings    Settings (keys and switches)   /api/settings   which keys exist (never the keys themselves)

Keys are the reader's own and stay in the file .env in {folder}. Do not read that file or
repeat a key back. Lists the reader keeps are plain files under {folder}/data/.
{profile}"""


# ---- the startup guide: five steps, each a link to the exact place; done is read off the desk ----
def _synced_folders():
    """Folders on this computer that a drive already syncs, where the vault could live."""
    home = os.path.expanduser("~")
    cands = [("iCloud Drive", os.path.join(home, "Library", "Mobile Documents", "com~apple~CloudDocs")),
             ("Google Drive", os.path.join(home, "Google Drive")), ("Dropbox", os.path.join(home, "Dropbox")),
             ("OneDrive", os.path.join(home, "OneDrive"))]
    cs = os.path.join(home, "Library", "CloudStorage")
    if os.path.isdir(cs):
        for d in sorted(os.listdir(cs)):
            cands.append((d.split("-")[0].replace("GoogleDrive", "Google Drive"), os.path.join(cs, d)))
    out, seen = [], set()
    for label, path in cands:
        if os.path.isdir(path) and path not in seen:
            seen.add(path)
            out.append({"label": label, "path": os.path.join(path, "GreekSoup")})
    return out


def build_guide():
    env = desk_settings.read_env()
    ticks = set(x for x in (env.get("GUIDE_TICKS") or "").split(",") if x)
    loc = desk_notes.vault_location()
    has_book = False
    try:
        has_book = bool(brokers.active_id()) or any(p.get("shares") for p in load_book().get("positions", []))
    except Exception:  # noqa: BLE001
        pass
    rd = ask_ready()
    has_ai = rd["ready"] or bool(rd.get("doors"))
    has_note = any(not n.get("example") for n in desk_notes.index().values())
    steps = [
        {"key": "vault", "label": "Where your research lives", "href": "/settings#vault",
         "done": (not loc["in_desk"]) or "vault" in ticks,
         "text": "Your notes, files, chains and lists are plain files in one folder. Keep them beside the desk, or in a folder a drive you already use syncs."},
        {"key": "book", "label": "Connect a broker, or start with the paper book", "href": "/settings",
         "done": has_book or "book" in ticks,
         "text": "A broker connects read-only on Settings; a book kept by hand lives on Desk · Book. Both price live."},
        {"key": "ai", "label": "Pick your AI", "href": "/settings#ai", "done": has_ai or "ai" in ticks,
         "text": "A key from a lab, a model running on this computer, or an app you already pay for through a door under Plugins."},
        {"key": "watch", "label": "Make your first list your own", "href": "/watch", "done": "watch" in ticks,
         "text": "Every list on the desk is yours: add a name to Watch, or open Your list on Funds, Capitol, Macro or Commodities."},
        {"key": "note", "label": "Save your first note", "href": "/notes?new", "done": has_note or "note" in ticks,
         "text": "A note on a name, a document brought in, or a dashboard of live blocks. Everything in your vault, nothing written until you save."},
    ]
    return {"shown": (env.get("GUIDE") or "").strip().lower() != "done", "steps": steps,
            "vault": {"path": loc["path"], "in_desk": loc["in_desk"], "documents": os.path.join(os.path.expanduser("~"), "Documents", "GreekSoup"),
                      "synced": _synced_folders()}}


def agent_page():
    prof = desk_settings.profile_text()
    block = ("\nHOW THIS READER INVESTS (from their Settings screen; shape answers to it)\n" + prof + "\n") if prof else ""
    return AGENT_PAGE.format(port=PORT, folder=HERE, profile=block)


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "[::1]", "")

    def _from_this_computer(self):
        """The two guards a desk with no login needs. Host: a request whose Host header is not
        this computer is a DNS-rebinding read from a web page and is refused. Origin: a browser
        names the page that made a cross-site request in Origin; any page that is not the
        desk's own is refused, which is what stops a web page elsewhere posting to Settings
        or reading the book. Programs on this computer (the reader's agent, curl) send no
        Origin and are let through, as they are the reader."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip().lower()
        if host.startswith("[") and not host.endswith("]"):
            host = host + "]"
        if host not in self.LOCAL_HOSTS:
            return False
        origin = self.headers.get("Origin")
        if origin and origin.lower() not in ("null",):
            oh = (urlparse(origin).hostname or "").lower()
            if oh not in ("localhost", "127.0.0.1", "::1"):
                return False
        elif origin:
            return False
        return True

    def _refuse(self):
        self.send_response(403)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"This desk answers only to its own computer and its own pages.")

    def do_GET(self):  # noqa: N802 - stdlib naming
        if not self._from_this_computer():
            return self._refuse()
        try:
            path = urlparse(self.path).path
            qs = parse_qs(urlparse(self.path).query)
            region = (qs.get("list", ["home"])[0] or "home").lower()
            if path in ("/", "/index.html"):
                with open(os.path.join(HERE, "web", "index.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path.startswith("/assets/"):
                # shared css/js only; the basename check keeps it inside the dir
                name = os.path.basename(path)
                full = os.path.join(HERE, "web", "assets", name)
                if not os.path.isfile(full):
                    return self.send_error(404)
                ctype = "text/css" if name.endswith(".css") else "application/javascript"
                with open(full, "rb") as fh:
                    self._send(fh.read(), f"{ctype}; charset=utf-8")
            elif path == "/watch":
                with open(os.path.join(HERE, "web", "watch.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/usdesk":
                # the US desk lives on Desk · Home since 2026-09-15.20; an old bookmark lands there
                self.send_response(302)
                self.send_header("Location", "/#usdesk")
                self.end_headers()
            elif path == "/t":
                with open(os.path.join(HERE, "web", "ticker.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/ping":
                return self._send(b'{"ok":true}', "application/json")
            elif path == "/api/nav":
                return self._send(json.dumps(nav_state()).encode(), "application/json")
            elif path == "/notes":
                with open(os.path.join(HERE, "web", "notes.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/notes":
                g = lambda k: (qs.get(k, [""])[0] or "").strip()[:120]  # noqa: E731
                return self._send(json.dumps({"notes": desk_notes.listing(g("symbol"), g("project"), g("type"), g("tag"), g("q"),
                                                                           g("kind"), g("period"), g("about"), g("status")),
                                              "statuses": desk_notes.STATUSES,
                                              "types": desk_notes.TYPES, "kinds": desk_notes.KINDS, "facets": desk_notes.facets(),
                                              "loose": desk_notes.loose_files(),
                                              "folder": desk_notes.RESEARCH_DIR}).encode(), "application/json")
            elif path == "/api/notes/get":
                n = desk_notes.get((qs.get("id", [""])[0] or "").strip())
                return self._send(json.dumps(n or {"error": "no such note"}).encode(), "application/json")
            elif path == "/api/notes/graph":
                return self._send(json.dumps(desk_notes.graph((qs.get("symbol", [""])[0] or "").strip())).encode(), "application/json")
            elif path.startswith("/plugins/"):
                # a file from one plugin's own folder: html, js, css, images; never anything else
                import mimetypes
                bits = path[len("/plugins/"):].split("/", 1)
                full = desk_plugins.file_path(bits[0], bits[1] if len(bits) > 1 else "") if bits and bits[0] else None
                if not full:
                    return self.send_error(404)
                with open(full, "rb") as fh:
                    body = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", (mimetypes.guess_type(full)[0] or "application/octet-stream") + ("; charset=utf-8" if full.endswith((".html", ".js", ".css", ".json", ".md", ".txt")) else ""))
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return self.wfile.write(body)
            elif path == "/api/plugins":
                return self._send(json.dumps({"installed": desk_plugins.installed(force=True), "doors": desk_plugins.doors(),
                                              "blocks": desk_plugins.block_files(), "folder": desk_plugins.plugins_dir(),
                                              "list_url": PLUGIN_LIST_URL}).encode(), "application/json")
            elif path == "/api/plugins/list":
                return self._send(json.dumps(plugin_list()).encode(), "application/json")
            elif path == "/api/research/block":
                spec = (qs.get("spec", [""])[0] or "")[:200]
                try:
                    return self._send(json.dumps(resolve_block(spec), default=str).encode(), "application/json")
                except Exception as exc:  # noqa: BLE001 - a block never breaks the note around it
                    return self._send(json.dumps({"spec": spec, "error": f"could not read this block ({type(exc).__name__})"}).encode(), "application/json")
            elif path == "/api/research/location":
                return self._send(json.dumps(desk_notes.vault_location()).encode(), "application/json")
            elif path == "/api/research/tree":
                return self._send(json.dumps(desk_notes.tree()).encode(), "application/json")
            elif path == "/api/research/tasks":
                sym = (qs.get("symbol", [""])[0] or "").strip()
                return self._send(json.dumps(desk_notes.tasks_view(calendar_rows(), sym or None)).encode(), "application/json")
            elif path == "/api/research/journal":
                return self._send(json.dumps({"mode": desk_notes.journal_mode(), "pending": desk_notes.journal_pending(),
                                              "days": desk_notes.journal_days()}).encode(), "application/json")
            elif path == "/api/research/drawings":
                try:
                    return self._send(json.dumps(desk_notes.drawings((qs.get("symbol", [""])[0] or "").strip())).encode(), "application/json")
                except ValueError as exc:
                    return self._send(json.dumps({"symbol": "", "items": [], "error": str(exc)}).encode(), "application/json")
            elif path == "/api/research/status":
                sym = (qs.get("symbol", [""])[0] or "").strip()
                if sym:
                    return self._send(json.dumps({**name_status(sym), "statuses": desk_notes.STATUSES}).encode(), "application/json")
                return self._send(json.dumps({"set": desk_notes.status_all(), "statuses": desk_notes.STATUSES}).encode(), "application/json")
            elif path == "/api/research/timeline":
                sym = (qs.get("symbol", [""])[0] or "").strip()
                out = desk_notes.timeline(sym)
                out["status"] = name_status(sym)
                return self._send(json.dumps(out).encode(), "application/json")
            elif path == "/api/research/context":
                # the reader's notes and files about one subject, as text: what the Ask box reads
                g = lambda k: (qs.get(k, [""])[0] or "").strip()[:120]  # noqa: E731
                return self._send(json.dumps(desk_notes.context(g("symbol") or None, g("kind") or None, g("about") or None)).encode(), "application/json")
            elif path == "/api/research/text":
                # what the desk read out of one attached file: the status, and the opening of the text
                rel = (qs.get("path", [""])[0] or "").strip()
                st = desk_notes.text_status(rel)
                if st.get("state") == "ready":
                    d = desk_notes.text_of(rel)
                    st["opening"] = (d or {}).get("text", "")[:1200]
                return self._send(json.dumps(st).encode(), "application/json")
            elif path == "/api/research/file":
                # a file the reader brought into the vault, served back to them: inline, so a
                # PDF or an image opens in the browser; never anything outside data/research/files
                import mimetypes
                full = desk_notes.file_path((qs.get("path", [""])[0] or "").strip())
                if not full or not os.path.isfile(full):
                    return self.send_error(404)
                ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
                with open(full, "rb") as fh:
                    body = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", f'inline; filename="{os.path.basename(full)}"')
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            elif path == "/settings":
                with open(os.path.join(HERE, "web", "settings.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/ask":
                self._send(json.dumps(ask_ready()).encode(), "application/json")
            elif path == "/api/ask/threads":
                self._send(json.dumps({"threads": ask_threads_list()}).encode(), "application/json")
            elif path == "/api/ask/thread":
                self._send(json.dumps({"thread": ask_thread_get((qs.get("id", [""])[0] or "").strip())}).encode(), "application/json")
            elif path == "/agent":
                self._send(agent_page().encode(), "text/plain; charset=utf-8")
            elif path == "/api/settings/backup":
                body = desk_settings.backup_zip()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="greeksoup-desk-backup-{datetime.now().strftime("%Y-%m-%d")}.zip"')
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            elif path == "/api/settings":
                self._send(json.dumps(settings_state()).encode(), "application/json")
            elif path == "/api/update":
                force = (qs.get("check", [""])[0] or "") == "1"
                self._send(json.dumps({**updater.status(force), "migrations": desk_migrate.last_report()}).encode(), "application/json")
            elif path == "/api/usbook":
                self._send(json.dumps(build_usbook()).encode(), "application/json")
            elif path == "/macro":
                with open(os.path.join(HERE, "web", "macro.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/commods":
                with open(os.path.join(HERE, "web", "commods.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/commods":
                self._send(json.dumps(_cached("commods", COMMODS_TTL, build_commods)).encode(),
                           "application/json")
            elif path == "/book":
                with open(os.path.join(HERE, "web", "book.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/book":
                self._send(json.dumps(_cached("book", BOOK_TTL, build_book)).encode(), "application/json")
            elif path == "/funds":
                with open(os.path.join(HERE, "web", "funds.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/capitol":
                with open(os.path.join(HERE, "web", "capitol.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/capitol":
                self._send(json.dumps(_cached("capitol", CAPITOL_TTL, build_capitol)).encode(), "application/json")
            elif path == "/chain":
                with open(os.path.join(HERE, "web", "chain.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/risk":
                with open(os.path.join(HERE, "web", "risk.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/risk":
                self._send(json.dumps(_cached("risk", RISK_TTL, build_risk)).encode(), "application/json")
            elif path == "/api/activist":
                self._send(json.dumps(_cached("act13d", ACT_TTL, build_activist)).encode(), "application/json")
            elif path == "/flow":
                with open(os.path.join(HERE, "web", "flow.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/flow":
                self._send(json.dumps(_cached("flow", FLOW_TTL, build_flow)).encode(), "application/json")
            elif path == "/calendar":
                with open(os.path.join(HERE, "web", "calendar.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/calendar":
                self._send(json.dumps(_cached("calendar", calendar_desk.TTL, build_calendar)).encode(), "application/json")
            elif path == "/short":
                with open(os.path.join(HERE, "web", "short.html"), "rb") as fh:
                    self._send(fh.read(), "text/html; charset=utf-8")
            elif path == "/api/short":
                self._send(json.dumps(_cached("short", SHORT_TTL, build_short)).encode(), "application/json")
            elif path == "/api/guide":
                self._send(json.dumps(build_guide()).encode(), "application/json")
            elif path == "/api/ai/app/check":
                self._send(json.dumps(desk_plugins.signed_in((qs.get("app", [""])[0] or "").strip())).encode(), "application/json")
            elif path == "/api/ai/apps":
                self._send(json.dumps({"apps": desk_plugins.apps_known(), "default_door": ask_ready()["default_door"]}).encode(), "application/json")
            elif path == "/api/lists":
                self._send(json.dumps({k: {"label": v["label"], "screen": v["screen"]} for k, v in desk_lists.KINDS.items()}).encode(), "application/json")
            elif path.startswith("/api/lists/"):
                kind = path.split("/")[3] if len(path.split("/")) > 3 else ""
                if kind not in desk_lists.KINDS:
                    return self.send_error(404)
                self._send(json.dumps(desk_lists.view(kind)).encode(), "application/json")
            elif path == "/api/chain":
                d = _cached("chain", CHAIN_TTL, build_chain)
                if "hidden_starters" not in (d or {}) or "markets" not in (d or {}):     # a copy from before chains were the reader's own, or before markets
                    _chain_changed()
                    d = _cache["chain"][1] or d
                self._send(json.dumps(d).encode(), "application/json")
            elif path == "/api/insiders":
                data = _cached("insiders", INSIDERS_TTL, build_insiders)
                self._send(json.dumps(data or {"error": "insider feed unreachable"}).encode(),
                           "application/json")
            elif path == "/api/infund":
                sym = (qs.get("symbol", [""])[0] or "").upper()
                if not sym:
                    return self.send_error(400)
                self._send(json.dumps(cached_infund(sym)).encode(), "application/json")
            elif path == "/api/alerts":
                with _alerts_lock:
                    body = json.dumps({"active": task_alerts() + ALERTS["active"],
                                       "rules": _load_alert_rules()})
                self._send(body.encode(), "application/json")
            elif path == "/api/search":
                q = (qs.get("q", [""])[0] or "")
                self._send(json.dumps({"results": search_symbols(q, region)}).encode(),
                           "application/json")
            elif path == "/api/earnings":
                self._send(json.dumps(_cached("earn", EARN_TTL, build_earnings)).encode(), "application/json")
            elif path in ("/api/results_home", "/api/earnings_in"):
                self._send(json.dumps(_cached("results_home", EARN_TTL, build_results_home)).encode(), "application/json")
            elif path == "/api/macro":
                self._send(json.dumps(_cached("macro", MACRO_TTL, build_macro)).encode(), "application/json")
            elif path == "/api/econcal":
                self._send(json.dumps(_cached("econcal", 6 * 3600, build_econcal)).encode(), "application/json")
            elif path == "/api/symbols":
                # Company name or ticker in, Yahoo's symbols out: what the Book and the
                # watchlists use so nobody has to know that Reliance is RELIANCE.NS.
                self._send(json.dumps(symbol_search(qs.get("q", [""])[0])).encode(), "application/json")
            elif path == "/api/pulse":
                self._send(json.dumps(_cached("pulse", 900, build_pulse)).encode(), "application/json")
            elif path == "/api/funds":
                self._send(json.dumps(_cached("funds", FUNDS_TTL, build_funds)).encode(), "application/json")
            elif path == "/api/ticker":
                sym = (qs.get("symbol", [""])[0] or "").upper().strip()
                if not sym:
                    return self.send_error(400)
                reg = (qs.get("region", ["us"])[0] or "us").lower()
                self._send(json.dumps(cached_ticker(sym, reg)).encode(), "application/json")
            elif path == "/api/candles":
                # the chart's bars at the size the reader picked: any Yahoo symbol, one of the
                # feed's own ranges and intervals, cached ten minutes per (symbol, range, interval)
                sym = (qs.get("symbol", [""])[0] or "").upper().strip()
                rng = (qs.get("range", ["1mo"])[0] or "1mo").lower()
                itv = (qs.get("interval", ["1d"])[0] or "1d").lower()
                if not sym or rng not in CANDLE_RANGES or itv not in CANDLE_INTERVALS:
                    return self.send_error(400)
                self._send(json.dumps(cached_candles(sym, rng, itv)).encode(), "application/json")
            elif path == "/api/fin":
                sym = (qs.get("symbol", [""])[0] or "").upper().strip()
                if not sym:
                    return self.send_error(400)
                self._send(json.dumps(cached_fin(sym)).encode(), "application/json")
            elif path == "/api/watch":
                with _watch_lock:
                    if region == "us":
                        data = {"region": "us", "quotes": WATCH_US,
                                "names": load_watchlist_us(),
                                "market_open": us_market_open(),
                                "provider": bool(os.getenv("FMP_API_KEY", "").strip())}
                    elif region == "global":
                        data = {"region": "global", "quotes": WATCH_GLOBAL,
                                "names": load_watchlist_global(),
                                "market_open": True}
                    else:
                        names = load_watchlist()
                        has_broker = _hook("quote") is not None
                        # a name that came through a broker is a broker code (RELIND), which only
                        # that broker can price; on a desk with no broker connected the row says
                        # so instead of sitting blank
                        for n in names:
                            n["broker_only"] = _is_broker_name(n) and not has_broker
                        data = {"region": "home", "quotes": WATCH,
                                "names": names,
                                "market_open": home_market_open(),
                                "market": _market_info(),
                                "has_book": has_broker,
                                "broker": has_broker,
                                "broker_only": sum(1 for n in names if n["broker_only"]),
                                "stream": _stream_healthy(),
                                "session_dead": broker_health["dead"] and has_broker}
                self._send(json.dumps(data).encode(), "application/json")
            elif path == "/api/snapshot":
                data = _cached("snap", SNAP_TTL, build_snapshot)
                self._send(json.dumps(data).encode(), "application/json")
            elif self.path == "/api/tape":
                data = _cached("tape", TAPE_TTL, build_tape)
                self._send(json.dumps(data).encode(), "application/json")
            else:
                self.send_error(404)
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001 - report, keep serving
            try:
                self.send_error(500, str(exc))
            except Exception:  # noqa: BLE001
                pass

    def _book_post(self, body):
        """Desk · Book edits: add/replace a line, remove one, import many,
        set cash. Writes data/book.json; places no orders anywhere."""
        book = load_book()
        book.setdefault("positions", []); book.setdefault("cash", [])
        def upsert(sym, shares, avg, name=None):
            book["positions"] = [p for p in book["positions"] if (p.get("symbol") or "").upper() != sym]
            book["positions"].append({"symbol": sym, "name": name or "", "shares": shares, "avg_cost": avg})
        if self.path == "/api/book/add":
            sym = str(body.get("symbol", "")).strip().upper()
            try:
                shares, avg = float(body.get("shares")), float(body.get("avg_cost"))
            except (TypeError, ValueError):
                return self._send(b'{"ok":false,"error":"shares and avg cost must be numbers"}', "application/json")
            q = fetch_yahoo_quote(sym) or freefeed.quote(sym)
            if not q:
                return self._send(json.dumps({"ok": False, "error": f"Yahoo has no quote for {sym}; use Yahoo's symbol (RELIANCE.NS, MC.PA, 0700.HK)"}).encode(), "application/json")
            upsert(sym, shares, avg, q.get("name"))
            save_book(book); _cache["book"] = (0.0, None)
            j = journal("book", sym, f"added to Desk · Book: {shares:g} units at {avg:g}")
            return self._send(json.dumps({"ok": True, "name": q.get("name"), "currency": q.get("currency"), "journal": j}).encode(), "application/json")
        if self.path == "/api/book/clear":
            had = len(book["positions"])
            book["positions"] = []
            save_book(book); _cache["book"] = (0.0, None)
            j = journal("book", "", f"Desk · Book cleared ({had} lines)") if had else None
            return self._send(json.dumps({"ok": True, "journal": j}).encode(), "application/json")
        if self.path == "/api/book/remove":
            sym = str(body.get("symbol", "")).strip().upper()
            had = any((p.get("symbol") or "").upper() == sym for p in book["positions"])
            book["positions"] = [p for p in book["positions"] if (p.get("symbol") or "").upper() != sym]
            save_book(book); _cache["book"] = (0.0, None)
            j = journal("book", sym, "removed from Desk · Book") if had else None
            return self._send(json.dumps({"ok": True, "journal": j}).encode(), "application/json")
        if self.path == "/api/book/import":
            lines, errors = _parse_book_lines(str(body.get("csv", "")))
            added = 0
            for ln in lines[:200]:
                q = fetch_yahoo_quote(ln["symbol"]) or freefeed.quote(ln["symbol"])
                if not q:
                    errors.append(f"{ln['symbol']}: no Yahoo quote")
                    continue
                upsert(ln["symbol"], ln["shares"], ln["avg_cost"], q.get("name"))
                added += 1
                time.sleep(0.4)
            save_book(book); _cache["book"] = (0.0, None)
            return self._send(json.dumps({"ok": True, "added": added, "errors": errors[:30]}).encode(), "application/json")
        if self.path == "/api/book/cash":
            ccy = str(body.get("currency", "")).strip().upper()
            try:
                amt = float(body.get("amount"))
            except (TypeError, ValueError):
                return self._send(b'{"ok":false,"error":"amount must be a number"}', "application/json")
            book["cash"] = [c for c in book["cash"] if (c.get("currency") or "").upper() != ccy] + [{"currency": ccy, "amount": amt}]
            save_book(book); _cache["book"] = (0.0, None)
            return self._send(b'{"ok":true}', "application/json")
        return self._send(b'{"ok":false,"error":"unknown book action"}', "application/json")

    def _settings_post(self, body):
        """The Settings screen. Only a page on this computer can call these: the
        JSON content type makes any other site's browser ask first, and the desk
        never answers that question."""
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            return self.send_error(400)
        if self.path == "/api/settings/save":
            fields = {k: v for k, v in body.items() if isinstance(v, str) and k in desk_settings.ALLOWED}
            if "DESK_AUTO_UPDATE" in fields:
                fields["DESK_AUTO_UPDATE"] = "on" if fields["DESK_AUTO_UPDATE"].lower() in ("on", "1", "true") else "off"
            if "JOURNAL" in fields and fields["JOURNAL"].lower() not in ("ask", "always", "never"):
                return self._send(b'{"ok":false,"error":"the journal takes ask, always or never"}', "application/json")
            if "AI_PROVIDER" in fields and fields["AI_PROVIDER"] and fields["AI_PROVIDER"] not in desk_ai.PROVIDERS:
                return self._send(b'{"ok":false,"error":"unknown provider"}', "application/json")
            if "AI_FORMAT" in fields and fields["AI_FORMAT"] and fields["AI_FORMAT"] not in desk_ai.FORMATS:
                return self._send(b'{"ok":false,"error":"unknown request shape"}', "application/json")
            if "DATA_PROVIDER" in fields:
                fields["DATA_PROVIDER"] = re.sub(r"[^a-z0-9_]", "", fields["DATA_PROVIDER"].lower())[:32]
            if "RISK_BENCHMARK" in fields:
                fields["RISK_BENCHMARK"] = re.sub(r"[^A-Za-z0-9^=.\-]", "", fields["RISK_BENCHMARK"].upper())[:24]
                fields["RISK_BENCHMARK_LABEL"] = re.sub(r"[^\w &.\-]", "", fields.get("RISK_BENCHMARK_LABEL", ""))[:40]
                _cache["risk"] = (0.0, None)
            if "HOME_MARKET" in fields:
                hm = re.sub(r"[^a-z0-9_]", "", fields["HOME_MARKET"].lower())[:16]
                if hm and hm not in markets.REGISTRY:
                    return self._send(b'{"ok":false,"error":"unknown market"}', "application/json")
                fields["HOME_MARKET"] = hm
            saved = desk_settings.write_env(fields)
            if "FMP_API_KEY" in saved:
                for k in ("earn", "capitol", "insiders", "econcal", "pulse"):
                    _cache[k] = (0.0, None)
            if "HOME_MARKET" in saved:
                for k in ("snap", "risk", "results_home", "macro", "econcal", "commods", "chain"):
                    _cache[k] = (0.0, None)
            return self._send(json.dumps({"ok": True, "saved": saved, "state": settings_state()}).encode(), "application/json")
        if self.path == "/api/settings/screens":
            # one screen shown or hidden; the choice outlives updates because it lives in .env
            key = str(body.get("key", "")).strip().lower()
            if key not in {sc[0] for sc in SCREENS} or key in ALWAYS_SHOWN:
                return self._send(b'{"ok":false,"error":"not a screen that can be hidden"}', "application/json")
            choices = screen_choices()
            if body.get("reset"):
                choices.pop(key, None)
            else:
                choices[key] = bool(body.get("show"))
            desk_settings.write_env({"SCREENS": ",".join(f"{k}:{'on' if v else 'off'}" for k, v in sorted(choices.items()))})
            os.environ["SCREENS"] = ",".join(f"{k}:{'on' if v else 'off'}" for k, v in sorted(choices.items()))
            return self._send(json.dumps({"ok": True, "nav": nav_state()}).encode(), "application/json")
        if self.path == "/api/settings/check_data":
            return self._send(json.dumps(desk_settings.check_fmp()).encode(), "application/json")
        if self.path == "/api/settings/check_ai":
            return self._send(json.dumps(desk_ai.ping()).encode(), "application/json")
        if self.path == "/api/settings/broker":
            # pick a broker and save its fields. "add": true keeps the ones already connected and
            # puts this one beside them (one per market); otherwise it replaces them. "" = no broker.
            bid = str(body.get("broker", "")).strip().lower()
            if bid and bid not in brokers.REGISTRY:
                return self._send(b'{"ok":false,"error":"unknown broker"}', "application/json")
            fields = {}
            mod = brokers.load(bid) if bid else None
            allowed = {f["env"]: f for f in (mod.META["fields"] if mod else [])}
            for k, v in (body.get("fields") or {}).items():
                if k in allowed and isinstance(v, str):
                    fields[k] = ("on" if v.lower() in ("on", "1", "true", "yes") else "off") if allowed[k].get("switch") else v
            ids = brokers.active_ids() if body.get("add") else []
            # two brokers in one market sit side by side on that market's desk, each its own block,
            # the desk's strip adding them (his ruling, 2026-09-17); the same broker twice waits on
            # keys per account
            if bid and bid not in ids:
                ids.append(bid)
            fields["BROKERS"] = ",".join(ids)
            fields["BROKER"] = ids[0] if ids else ""
            desk_settings.write_env(fields)
            rep = {"ok": True}
            if bid:
                rep = connect_broker_now(bid)
                if rep.get("need_token"):
                    rep["ok"] = True   # keys saved; the login comes next
                    rep["saved_only"] = True
            else:
                connect_broker_now("")
            rep["state"] = settings_state()
            return self._send(json.dumps(rep).encode(), "application/json")
        if self.path == "/api/settings/broker/test":
            rep = connect_broker_now(str(body.get("broker", "") or ""))
            rep["state"] = settings_state()
            return self._send(json.dumps(rep).encode(), "application/json")
        if self.path == "/api/settings/broker/remove":
            bid = str(body.get("broker", "")).strip().lower()
            if bid not in brokers.active_ids():
                return self._send(b'{"ok":false,"error":"that broker is not on this desk"}', "application/json")
            mod = brokers.load(bid)
            disconnect_broker(bid)
            if body.get("keys"):
                desk_settings.write_env({f["env"]: ("off" if f.get("switch") else "") for f in mod.META["fields"]})
            return self._send(json.dumps({"ok": True, "state": settings_state()}).encode(), "application/json")
        if self.path == "/api/settings/token":
            bid = str(body.get("broker", "") or "").strip().lower() or next((b for b in brokers.active_ids() if brokers.load(b).META["daily_login"]), brokers.active_id())
            mod = brokers.load(bid) if bid else None
            if not mod or not mod.META["daily_login"]:
                return self._send(b'{"ok":false,"error":"The chosen broker has no daily login."}', "application/json")
            if not brokers.configured(bid):
                return self._send(b'{"ok":false,"error":"Save the broker keys first, then log in."}', "application/json")
            raw = str(body.get("token", "")).strip()
            # a whole redirect address pasted by mistake still works
            m = re.search(re.escape(mod.META.get("token_param", "token")) + r"=([^&\s]+)", raw)
            if m:
                raw = m.group(1)
            if not raw:
                return self._send(b'{"ok":false,"error":"Paste what the login handed back first."}', "application/json")
            try:
                access = mod.exchange_token(brokers.config(bid), raw)
            except brokers.BrokerError as exc:
                return self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")
            brokers.write_token(access, bid)
            rep = connect_broker_now(bid)
            if not rep.get("ok"):
                brokers.clear_token(bid)
            rep["state"] = settings_state()
            return self._send(json.dumps(rep).encode(), "application/json")
        if self.path == "/api/settings/profile":
            prof = desk_settings.save_profile(body)
            return self._send(json.dumps({"ok": True, "profile": prof}).encode(), "application/json")
        if self.path == "/api/settings/autostart":
            rep = desk_settings.set_autostart(bool(body.get("on")))
            rep["status"] = desk_settings.autostart_status()
            return self._send(json.dumps(rep).encode(), "application/json")
        return self._send(b'{"ok":false,"error":"unknown settings action"}', "application/json")

    def _ask_post(self, body):
        """The Ask box: the reader's question, with the numbers of the screen they are
        on, to the AI they set in Settings. Reads the desk; writes nothing."""
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            return self.send_error(400)
        question = str(body.get("question", "")).strip()[:4000]
        if not question:
            return self._send(b'{"ok":false,"error":"Type a question first."}', "application/json")
        rd = ask_ready()
        door = str(body.get("door", "") or "") if "door" in body else rd["default_door"]
        if not door and not rd["ready"]:
            return self._send(json.dumps({"ok": False, "error": rd["why"], "settings": True}).encode(), "application/json")
        page = str(body.get("page", "/"))
        history = body.get("history") if isinstance(body.get("history"), list) else []
        mode = str(body.get("mode", "")) if str(body.get("mode", "")) in ("build", "web") else "research"
        model = str(body.get("model", "") or "").strip()[:80]
        ask_id = re.sub(r"[^a-z0-9]", "", str(body.get("id", "")))[:24]
        if mode == "build":
            # Build: the reader asked the app on this computer to change the desk itself. Only a
            # door can (a key answers, it cannot act); the app runs in the desk's own folder
            # with its edits allowed, and says what it changed.
            if not door:
                return self._send(b'{"ok":false,"error":"Changing the desk needs an app on this computer (Claude Code, Codex, Gemini CLI); a key can only answer. Pick one above."}', "application/json")
            label, _, _ = ask_context(page, body.get("query") or {}, "")
            out = desk_plugins.run_door(door, desk_ai.build_prompt(question, label, AGENT_PAGE.format(port=PORT), history), mode="build", timeout=900, model=model, ask_id=ask_id)
            out["model"] = out.pop("via", door)
            out["read"] = ["the desk's own folder"]
            out["screen"] = label
            out["mode"] = "build"
            return self._send(json.dumps(out).encode(), "application/json")
        label, context, used = ask_context(page, body.get("query") or {}, question)
        desk_map = _desk_map_text()
        web = mode == "web"
        # on a listing's page the pictures the reader kept on it (chart clippings, screenshots) go
        # along: as pictures to a key, as files on this computer to an app
        qsym = re.sub(r"[^A-Za-z0-9.^=-]", "", str((body.get("query") or {}).get("symbol", "") if isinstance(body.get("query"), dict) else ""))[:40]
        pictures = desk_notes.pictures(symbol=qsym) if page == "/t" and qsym else []
        def _ask(ctx):
            if door:
                # a door: the same brief, handed to a command on this computer (the reader's coding agent);
                # with the web too, the app's own search flags go on and the brief says to cite
                o = desk_plugins.run_door(door, desk_ai.door_prompt(question, label, ctx, desk_settings.profile_text(), history, desk_map, web=web, pictures=pictures),
                                          mode="web" if web else "research", timeout=480 if web else 240, model=model, ask_id=ask_id)
                o["model"] = o.pop("via", door)
            else:
                s = desk_ai.settings()
                if model:
                    s["model"] = model     # the model the reader picked in the box, over the one on Settings
                o = desk_ai.ask(question, label, ctx, desk_settings.profile_text(), history, s=s, desk_map=desk_map, web=web, pictures=pictures)
                o["model"] = s["model"]
            return o
        out = _ask(context)
        # a second round when the model names the screens it still needs, once
        more = ask_more(out.get("answer", ""), set(used)) if out.get("ok") else []
        if more:
            parts, used2, _ = ask_fetch(more, ASK_CAP // 2, extra=True)
            out = _ask(context + "\n\nMORE OF THE DESK, AS YOU ASKED\n" + "\n\n".join(parts))
            used += used2
        if out.get("ok") and re.match(r"^\s*NEED:", out.get("answer", "")):
            out["answer"] = "I would need " + out["answer"].strip()[5:].strip() + " for that, and could not read it this time. Try the question once more, or ask on that screen."
        out["read"] = used + ([f"{len(pictures)} picture{'s' if len(pictures) != 1 else ''} from your notes"] if pictures and out.get("ok") else []) + (["the web"] if web and out.get("ok") else [])
        out["screen"] = label
        return self._send(json.dumps(out).encode(), "application/json")

    def do_POST(self):  # noqa: N802 - stdlib naming
        """Every edit the desk accepts. Still zero order capability anywhere. A request from a
        page that is not the desk's own, or with a Host that is not this computer, is refused
        before it is read."""
        if not self._from_this_computer():
            return self._refuse()
        try:
            length = int(self.headers.get("Content-Length", 0))
            if self.path.startswith("/api/settings/restore"):
                # a backup back in: raw zip bytes; data/ files written, changed ones kept aside first
                data = self.rfile.read(length)
                try:
                    rep = desk_settings.restore_zip(data)
                except ValueError as exc:
                    return self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")
                # what the desk holds in memory follows the files
                for kind in ("book",):
                    _cache[kind] = (0.0, None)
                desk_notes.index(force=True)
                desk_plugins.installed(force=True)
                return self._send(json.dumps({"ok": True, **rep}).encode(), "application/json")
            if self.path.startswith("/api/plugins/install_zip"):
                q = parse_qs(urlparse(self.path).query)
                data = self.rfile.read(length)
                try:
                    p = desk_plugins.install_zip(data, (q.get("name", [""])[0] or "").strip())
                    return self._send(json.dumps({"ok": True, "plugin": p}).encode(), "application/json")
                except ValueError as exc:
                    return self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")
            if self.path.startswith("/api/research/upload"):
                # a file the reader is bringing into the vault, sent as its own bytes; it is
                # stored under files/<subject>/ and nothing else happens until the note is saved
                q = parse_qs(urlparse(self.path).query)
                g = lambda k: (q.get(k, [""])[0] or "").strip()[:200]  # noqa: E731
                if length > desk_notes.FILE_CAP:
                    return self._send(b'{"ok":false,"error":"that file is larger than the desk keeps (200 MB)"}', "application/json")
                data = self.rfile.read(length)
                try:
                    rel = desk_notes.store_file(g("name"), data, g("symbol"), g("about"))
                except ValueError as exc:
                    return self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")
                return self._send(json.dumps({"ok": True, "file": rel, "size": len(data), "type": desk_notes.file_type(rel)}).encode(), "application/json")
            body = json.loads(self.rfile.read(length) or b"{}")
            region = str(body.get("list", "home")).lower()
            code = str(body.get("code", "")).strip().upper()
            if self.path.startswith("/api/book/"):
                return self._book_post(body)
            if self.path.startswith("/api/chain/"):
                return _chain_post(self, body)
            if self.path.startswith("/api/lists/"):
                return _lists_post(self, body)
            if self.path == "/api/ai/app/use":
                door, app = str(body.get("door", "") or ""), str(body.get("app", "") or "")
                if not door and app:
                    # the app is on this computer but no door reaches it yet: the shipped Terminal door goes in
                    try:
                        desk_plugins.install_shipped("terminal")
                    except (ValueError, OSError) as exc:
                        return self._send(json.dumps({"ok": False, "error": f"The Terminal door could not be installed ({exc})."}).encode(), "application/json")
                    door = next((d["name"] for d in desk_plugins.doors() if d["app"] == app and d["ready"]), "")
                    if not door:
                        return self._send(b'{"ok":false,"error":"the app was not found from the desk"}', "application/json")
                if door and not any(d["name"] == door for d in desk_plugins.doors()):
                    return self._send(b'{"ok":false,"error":"no such app on this computer"}', "application/json")
                desk_settings.write_env({"AI_DOOR": door})
                return self._send(json.dumps({"ok": True, "default_door": ask_ready()["default_door"]}).encode(), "application/json")
            if self.path == "/api/ai/app/signin":
                return self._send(json.dumps(open_signin_window(str(body.get("app", "")))).encode(), "application/json")
            if self.path == "/api/guide":
                # the reader's own ticks, Done, and Show it again; nothing else is written
                env = desk_settings.read_env()
                ticks = set(x for x in (env.get("GUIDE_TICKS") or "").split(",") if x)
                if body.get("tick") in ("vault", "book", "ai", "watch", "note"):
                    ticks = (ticks | {body["tick"]}) if body.get("on", True) else (ticks - {body["tick"]})
                    desk_settings.write_env({"GUIDE_TICKS": ",".join(sorted(ticks))})
                if body.get("done"):
                    desk_settings.write_env({"GUIDE": "done"})
                if body.get("again"):
                    desk_settings.write_env({"GUIDE": ""})
                return self._send(json.dumps({"ok": True, **build_guide()}).encode(), "application/json")
            if self.path == "/api/notes/save":
                try:
                    note = desk_notes.save(body)
                    j = journal("note", (note.get("symbols") or [""])[0] or "", note_moment(note)) if note.get("new") else None
                    return self._send(json.dumps({"ok": True, "note": note, "journal": j}).encode(), "application/json")
                except ValueError as exc:
                    return self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")
            if self.path == "/api/notes/delete":
                return self._send(json.dumps({"ok": desk_notes.delete(str(body.get("id", "")), bool(body.get("with_file")))}).encode(), "application/json")
            if self.path == "/api/plugins/install":
                try:
                    if body.get("from_list"):
                        p = install_from_list(str(body["from_list"]))
                    else:
                        p = desk_plugins.install_folder(str(body.get("folder", "")))
                    return self._send(json.dumps({"ok": True, "plugin": p}).encode(), "application/json")
                except (ValueError, OSError) as exc:
                    return self._send(json.dumps({"ok": False, "error": str(exc)[:300]}).encode(), "application/json")
            if self.path == "/api/plugins/remove":
                return self._send(json.dumps({"ok": desk_plugins.remove(str(body.get("name", "")))}).encode(), "application/json")
            if self.path == "/api/research/relocate":
                try:
                    target = desk_notes.DEFAULT_RESEARCH_DIR if body.get("default") else str(body.get("path", ""))
                    rep = desk_notes.relocate(target)
                    desk_settings.write_env({"RESEARCH_DIR": "" if body.get("default") else rep["path"]})
                    desk_plugins.installed(force=True)
                    _cache["book"] = (0.0, None)
                    return self._send(json.dumps({"ok": True, **rep, "location": desk_notes.vault_location()}).encode(), "application/json")
                except (ValueError, OSError) as exc:
                    return self._send(json.dumps({"ok": False, "error": str(exc)[:300]}).encode(), "application/json")
            if self.path == "/api/research/tasks/add":
                try:
                    t = desk_notes.add_task(str(body.get("text", "")), str(body.get("symbol", "")), str(body.get("due", "")),
                                            str(body.get("category", "")), str(body.get("source", "you")))
                    return self._send(json.dumps({"ok": True, "task": t}).encode(), "application/json")
                except ValueError as exc:
                    return self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")
            if self.path == "/api/research/tasks/tick":
                done = bool(body.get("done", True))
                if body.get("note_id"):
                    n = desk_notes.tick_note_task(str(body["note_id"]), int(body.get("line", -1)), done)
                    return self._send(json.dumps({"ok": bool(n)}).encode(), "application/json")
                if int(body.get("line", -1)) < 0 and body.get("task"):
                    # a task the calendar made: ticking it writes it down as done, so it stays ticked
                    ct = body["task"]
                    t = desk_notes.add_task(str(ct.get("text", "")), str(ct.get("symbol", "")), str(ct.get("due", "")), "results", "calendar")
                    t = desk_notes.tick_task(t["line"], True)
                else:
                    t = desk_notes.tick_task(int(body.get("line", -1)), done)
                j = journal("task", (t or {}).get("symbol", ""), f"task done: {t['text']}") if t and done else None
                return self._send(json.dumps({"ok": bool(t), "task": t, "journal": j}).encode(), "application/json")
            if self.path == "/api/research/tasks/delete":
                return self._send(json.dumps({"ok": desk_notes.delete_task(int(body.get("line", -1)))}).encode(), "application/json")
            if self.path == "/api/research/journal/decide":
                ok = desk_notes.journal_decide(str(body.get("id", "")), bool(body.get("write")), str(body.get("why", "")))
                return self._send(json.dumps({"ok": ok, "pending": len(desk_notes.journal_pending())}).encode(), "application/json")
            if self.path == "/api/research/journal/why":
                ok = desk_notes.journal_why(str(body.get("date", "")), int(body.get("line", -1)), str(body.get("why", "")))
                return self._send(json.dumps({"ok": ok}).encode(), "application/json")
            if self.path == "/api/research/journal/add":
                # the reader's own line, written straight in
                text = str(body.get("text", "")).strip()[:300]
                if not text:
                    return self._send(b'{"ok":false,"error":"Write a line first."}', "application/json")
                e = {"id": "", "at": datetime.now().strftime("%Y-%m-%d %H:%M"), "what": "you", "symbol": str(body.get("symbol", "")).upper()[:24], "text": text}
                return self._send(json.dumps({"ok": True, **desk_notes.journal_write(e, str(body.get("why", "")))}).encode(), "application/json")
            if self.path in ("/api/research/drawings/add", "/api/research/drawings/remove"):
                # the reader's drawings on a name's chart; add takes the drawing, remove takes an id (none clears the chart)
                try:
                    if self.path.endswith("/add"):
                        d = desk_notes.add_drawing(str(body.get("symbol", "")), body.get("item") or {})
                    else:
                        d = desk_notes.remove_drawing(str(body.get("symbol", "")), str(body.get("id", "") or "") or None)
                    return self._send(json.dumps({"ok": True, **d}).encode(), "application/json")
                except (ValueError, TypeError) as exc:
                    return self._send(json.dumps({"ok": False, "error": str(exc) if isinstance(exc, ValueError) else "a drawing needs a time and a price"}).encode(), "application/json")
            if self.path == "/api/research/status":
                try:
                    before = desk_notes.status_all().get(str(body.get("symbol", "")).upper(), {}).get("status", "")
                    st = desk_notes.set_status(str(body.get("symbol", "")), str(body.get("status", "")))
                    j = None
                    if st["status"] != before:
                        j = journal("status", st["symbol"], f"status set to {st['status']}" if st["status"] else "status cleared")
                    return self._send(json.dumps({"ok": True, "status": name_status(st["symbol"]), "journal": j}).encode(), "application/json")
                except ValueError as exc:
                    return self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")
            if self.path == "/api/research/remove_file":
                return self._send(json.dumps({"ok": desk_notes.remove_file(str(body.get("file", "")))}).encode(), "application/json")
            if self.path == "/api/notes/detach":
                n = desk_notes.detach(str(body.get("id", "")), bool(body.get("delete_file")))
                return self._send(json.dumps({"ok": bool(n), "note": n}).encode(), "application/json")
            if self.path.startswith("/api/settings/"):
                return self._settings_post(body)
            if self.path == "/api/ask":
                return self._ask_post(body)
            if self.path == "/api/ask/stop":
                return self._send(json.dumps({"ok": desk_plugins.stop_door(str(body.get("id", "")))}).encode(), "application/json")
            if self.path == "/api/ask/thread/save":
                return self._send(json.dumps({"ok": True, "thread": ask_thread_save(body)}).encode(), "application/json")
            if self.path == "/api/ask/thread/delete":
                return self._send(json.dumps({"ok": ask_thread_delete(str(body.get("id", "")))}).encode(), "application/json")
            if self.path == "/api/update/apply":
                # The one click. Writes program files inside this folder only,
                # then the process restarts itself; the page reconnects.
                rep = updater.apply()
                rep["folder"] = HERE
                if rep.get("ok"):
                    rep["restarting"] = True
                    updater.restart_soon(1.5)
                return self._send(json.dumps(rep).encode(), "application/json")
            if self.path == "/api/watch/add":
                if not code:
                    return self._send(b'{"ok":false,"error":"empty code"}', "application/json")
                if region == "us":
                    names = load_watchlist_us()
                    if any(n["code"] == code for n in names):
                        return self._send(b'{"ok":false,"error":"already on the list"}', "application/json")
                    q = fetch_us_quote(code) or freefeed.quote(code)
                    if not q:
                        return self._send(
                            json.dumps({"ok": False, "error": f"no quote for {code} - check the ticker"}).encode(),
                            "application/json")
                    names.append({"code": code, "source": "fmp"})
                    save_watchlist_us(names)
                    with _watch_lock:
                        WATCH_US[code] = q
                    _spawn("flow", build_flow)      # Flow reads the new name's chain behind the page
                    _spawn("short", build_short)    # and Short its FINRA rows
                    return self._send(json.dumps({"ok": True, "journal": journal("watch", code, f"added to {WATCH_LABEL.get(region, 'Watch')}")}).encode(), "application/json")
                if region == "global":
                    names = load_watchlist_global()
                    if any(n["code"] == code for n in names):
                        return self._send(b'{"ok":false,"error":"already on the list"}', "application/json")
                    q = fetch_yahoo_quote(code)
                    if not q:
                        return self._send(
                            json.dumps({"ok": False, "error": f"no Yahoo quote for {code}; use Yahoo symbols like TALABAT.AE"}).encode(),
                            "application/json")
                    names.append({"code": code, "source": "yahoo"})
                    save_watchlist_global(names)
                    with _watch_lock:
                        WATCH_GLOBAL[code] = q
                    return self._send(json.dumps({"ok": True, "journal": journal("watch", code, f"added to {WATCH_LABEL.get(region, 'Watch')}")}).encode(), "application/json")
                names = load_watchlist()
                m = _market()
                exch = str(body.get("exch", "")).strip().upper() or (m.META["exchanges"][0] if m else "")
                if any(n["code"] == code for n in names):
                    return self._send(b'{"ok":false,"error":"already on the list"}', "application/json")
                via_broker = _hook("quote") is not None
                q = _home_quote(code, exch or None)
                if not q and not via_broker and "." not in code and m is None:
                    q = fetch_yahoo_quote(code)
                if not q:
                    where = (" on " + " or ".join(m.META["exchanges"])) if m else ""
                    hint = ("check the code your broker uses" if via_broker
                            else "use the exchange symbol, or Yahoo's symbol when no home market is set (AAPL, RELIANCE.NS, MC.PA)")
                    return self._send(
                        json.dumps({"ok": False, "error": f"no quote for {code}{where}; {hint}"}).encode(),
                        "application/json")
                names.append({"code": code, "exch": q.get("exch") or exch,
                              "source": "broker" if via_broker else "yahoo"})
                save_watchlist(names)
                with _watch_lock:
                    WATCH[code] = q
                return self._send(json.dumps({"ok": True, "journal": journal("watch", code, f"added to {WATCH_LABEL.get(region, 'Watch')}")}).encode(), "application/json")
            if self.path == "/api/watch/remove":
                if region == "us":
                    save_watchlist_us([n for n in load_watchlist_us() if n["code"] != code])
                    with _watch_lock:
                        WATCH_US.pop(code, None)
                    _spawn("flow", build_flow)
                    _spawn("short", build_short)
                elif region == "global":
                    save_watchlist_global([n for n in load_watchlist_global() if n["code"] != code])
                    with _watch_lock:
                        WATCH_GLOBAL.pop(code, None)
                else:
                    save_watchlist([n for n in load_watchlist() if n["code"] != code])
                    with _watch_lock:
                        WATCH.pop(code, None)
                return self._send(json.dumps({"ok": True, "journal": journal("watch", code, f"removed from {WATCH_LABEL.get(region, 'Watch')}")}).encode(), "application/json")
            self.send_error(404)
        except Exception as exc:  # noqa: BLE001
            self._send(json.dumps({"ok": False, "error": str(exc)}).encode(), "application/json")

    def log_message(self, *args):  # quiet
        pass


def main():
    try:
        gone = updater.tidy()
        if gone:
            print("removed from the desk folder (the website and the installers, not needed here): " + ", ".join(gone))
    except Exception as exc:  # noqa: BLE001 - tidying must never stop the desk
        print("tidy skipped:", exc)
    mig = desk_migrate.run(updater.local_version())
    try:
        for nm in desk_plugins.refresh_shipped():
            print(f"plugin {nm} brought up to the version that ships with this desk")
    except Exception as exc:  # noqa: BLE001 - a plugin must never stop the desk
        print("plugins: refresh skipped:", exc)
    for m in mig["migrated"]:
        if not m["stamped"]:
            print(f"  brought {m['label']} up to this version's shape ({os.path.relpath(m['path'], HERE)}); the copy from before is at {os.path.relpath(m['kept'], HERE)}")
    for n in mig["newer"]:
        print(f"  NOTE: {os.path.relpath(n['path'], HERE)} was written by a newer desk; update this one to read it fully")
    if brokers.active_ids():
        for bid, rep in connect_all_brokers().items():
            label = brokers.load(bid).META["label"]
            if rep.get("ok"):
                print(f"  {label}: connected as {rep.get('label')}, {rep.get('positions')} holdings")
            else:
                print(f"  {label}: not connected: {rep.get('error')}")
    broker_health["dead"] = not clients
    if not clients:
        print("  NOTE: no broker session. Desk · Home shows the last saved book (or nothing "
              "on a fresh install) until a broker is connected on Settings; everything else runs.")
    hm = _market()
    print(f"  home market: {hm.META['label'] if hm else 'none set (follows the broker, or HOME_MARKET in .env)'}")
    # Dead tokens must not cost the account-number labels 
    # or re-fire yesterday's alert chips — both restore from disk.
    prev_snap = load_last_snapshot()
    if prev_snap:
        for account, a in prev_snap.get("data", {}).get("accounts", {}).items():
            if ACCOUNT_LABELS.get(account, account) == account and a.get("label"):
                ACCOUNT_LABELS[account] = a["label"]
    _restore_alerts()
    restore_quotes()
    threading.Thread(target=watch_loop, daemon=True).start()
    threading.Thread(target=us_watch_loop, daemon=True).start()
    threading.Thread(target=global_watch_loop, daemon=True).start()
    threading.Thread(target=alerts_loop, daemon=True).start()
    threading.Thread(target=quote_saver_loop, daemon=True).start()
    threading.Thread(target=updater.loop, daemon=True).start()

    REFRESH = (("earn", EARN_TTL, build_earnings),
               ("macro", MACRO_TTL, build_macro),
               ("capitol", CAPITOL_TTL, build_capitol),
               ("funds", FUNDS_TTL, build_funds),
               ("results_home", EARN_TTL, build_results_home),
               ("insiders", INSIDERS_TTL, build_insiders),
               ("risk", RISK_TTL, build_risk),
               ("act13d", ACT_TTL, build_activist),
               ("flow", FLOW_TTL, build_flow),
               ("short", SHORT_TTL, build_short),
               ("calendar", calendar_desk.TTL, build_calendar),
               ("commods", COMMODS_TTL, build_commods),
               ("chain", CHAIN_TTL, build_chain))

    def warmup():
        # first pass builds every slow cache once so the first click on any
        # tab is instant; after that the loop keeps each one fresh in the
        # background on its TTL, so a click never waits for a rebuild
        while True:
            for kind, ttl, builder in REFRESH:
                stamp, data = _cache[kind]
                if data is None or time.time() - stamp >= _ttl_of(data, ttl):
                    try:
                        _cached(kind, ttl, builder)
                    except Exception:  # noqa: BLE001
                        pass
                    time.sleep(2)
            time.sleep(20)
    threading.Thread(target=warmup, daemon=True).start()
    print(f"\nDesk is live:  http://localhost:{PORT}")
    print(f"Watch Home:    http://localhost:{PORT}/watch")
    print(f"Watch US:      http://localhost:{PORT}/watch?list=us\nCtrl+C to stop.")
    try:
        # Answer on both of this computer's own addresses. On Windows the name
        # "localhost" is usually the IPv6 one first, so a desk listening only on the
        # IPv4 address can look absent to anything that does not fall back. Neither
        # address is reachable from another machine.
        class _Localhost6(ThreadingHTTPServer):
            address_family = socket.AF_INET6

        try:
            six = _Localhost6(("::1", PORT), Handler)
            threading.Thread(target=six.serve_forever, daemon=True).start()
        except OSError:
            pass          # no IPv6 on this computer, or already answering there
        four = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
        # Once the door is ours, leave this process number in the folder, so Stop Desk
        # and Uninstall Desk can find exactly this copy. On Windows a desk started
        # through its .venv runs as a child of a launcher, so neither its program path
        # nor its command line names the folder, and the port alone cannot tell two
        # copies apart. Written only after the bind, so a second start that finds the
        # door taken never overwrites the running desk's number.
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            os.makedirs(os.path.join(here, "logs"), exist_ok=True)
            with open(os.path.join(here, "logs", "desk.pid"), "w") as f:
                f.write(str(os.getpid()))
        except OSError:
            pass
        four.serve_forever()
    except OSError:
        print(f"\nThe desk is already running at http://localhost:{PORT} — nothing to do.")


if __name__ == "__main__":
    main()
