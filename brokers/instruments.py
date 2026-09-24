"""One stock, every broker's name for it (India).

The desk speaks one language for a home name: the exchange symbol and the exchange
(RELIANCE on NSE). Brokers do not all ask for a price that way. Zerodha and Groww take
the symbol, Upstox takes the ISIN (NSE_EQ|INE002A01018), and Angel One and Dhan take the
exchange's own number for the stock (2885 for RELIANCE on NSE). That number is the
exchange's, not the broker's: checked 2026-09-24, all 2,670 NSE equities that appear in
the Upstox, Angel One and Dhan instrument files carry the same number in all three.

So one public file covers every broker: Upstox publishes the NSE and BSE lists with the
symbol, the ISIN and the exchange number side by side, no login needed
(upstox.com/developer/api-documentation/instruments). The desk fetches the list for an
exchange once a day into cache/, keeps the last good copy when the fetch fails, and a
broker file asks lookup() for the one field it needs. A broker added later declares
which field that is and gets every stock without a list of its own.
"""
import gzip
import json
import os
import threading
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.dirname(HERE), "cache")
SOURCE = "https://assets.upstox.com/market-quote/instruments/exchange/{exch}.json.gz"
SEGMENT = {"NSE": "NSE_EQ", "BSE": "BSE_EQ"}
MAX_AGE = 20 * 3600

_maps = {}          # exch -> {"at": fetched, "rows": {SYMBOL: [isin, token, name]}}
_lock = threading.Lock()


def _path(exch):
    return os.path.join(CACHE, f"instruments_{exch}.json")


def parse(rows, exch):
    """The published list -> {SYMBOL: [isin, token, name]} for the exchange's equities."""
    seg = SEGMENT[exch]
    out = {}
    for r in rows or []:
        if r.get("segment") != seg:
            continue
        sym = str(r.get("trading_symbol") or "").upper()
        if sym:
            out[sym] = [r.get("isin") or "", str(r.get("exchange_token") or ""), r.get("name") or ""]
    return out


def _fetch(exch):
    r = requests.get(SOURCE.format(exch=exch), timeout=60)
    r.raise_for_status()
    return parse(json.loads(gzip.decompress(r.content)), exch)


def _load(exch):
    now = time.time()
    held = _maps.get(exch)
    if held and now - held["at"] < MAX_AGE:
        return held["rows"]
    path = _path(exch)
    try:
        with open(path) as fh:
            disk = json.load(fh)
    except (OSError, ValueError):
        disk = None
    if disk and now - disk.get("at", 0) < MAX_AGE:
        _maps[exch] = disk
        return disk["rows"]
    try:
        rows = _fetch(exch)
    except Exception:  # noqa: BLE001 - a missed day keeps yesterday's list
        rows = None
    if rows:
        fresh = {"at": now, "source": SOURCE.format(exch=exch), "rows": rows}
        _maps[exch] = fresh
        try:
            os.makedirs(CACHE, exist_ok=True)
            with open(path, "w") as fh:
                json.dump(fresh, fh)
        except OSError:
            pass
        return rows
    if disk:
        _maps[exch] = {"at": now - MAX_AGE + 3600, "rows": disk["rows"]}   # try the fetch again in an hour
        return disk["rows"]
    return {}


def lookup(symbol, exch="NSE"):
    """{"symbol", "exch", "isin", "token", "name"} for an exchange symbol, None when the
    exchange's list does not carry it (or no list could be had)."""
    exch = (exch or "NSE").upper()
    if exch not in SEGMENT:
        return None
    with _lock:
        rows = _load(exch)
    hit = rows.get(str(symbol or "").upper())
    if not hit:
        return None
    return {"symbol": str(symbol).upper(), "exch": exch, "isin": hit[0], "token": hit[1], "name": hit[2]}
