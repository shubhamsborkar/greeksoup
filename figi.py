"""An ISIN in, the listings out. OpenFIGI is Bloomberg's open identifier service: it maps an
ISIN (the twelve-character code every broker statement and every filing prints) to the
ticker and exchange of every listing that carries it, keyless, with a modest rate limit.
The desk uses it in one place: when what a reader types into a search box is an ISIN,
the listings come from here and the free feed's symbol is spelled from the exchange code,
so a line pasted from a statement prices without anyone guessing the ticker.

Keyless calls are limited (about twenty-five a minute), so every answer is kept on disk and
an ISIN is asked once.
"""

import json
import os
import re
import threading
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(HERE, "cache", "figi.json")
ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_lock = threading.Lock()

# OpenFIGI exchange code -> the free feed's suffix. Composite codes first (US, IN); the
# rest are the exchanges the desk's market files and readers have met so far.
SUFFIX = {
    "US": "", "UN": "", "UW": "", "UQ": "", "UA": "", "UR": "", "UP": "",
    "IN": ".NS", "IS": ".NS", "IB": ".BO",
    "LN": ".L", "GR": ".DE", "GY": ".DE", "FP": ".PA", "NA": ".AS", "SW": ".SW", "SE": ".SW",
    "IM": ".MI", "SM": ".MC", "BB": ".BR", "PL": ".LS", "DC": ".CO", "SS": ".ST", "NO": ".OL",
    "FH": ".HE", "AV": ".VI", "ID": ".IR", "PW": ".WA",
    "JP": ".T", "JT": ".T", "HK": ".HK", "AU": ".AX", "NZ": ".NZ", "SP": ".SI", "KS": ".KS",
    "TT": ".TW", "CH": ".SS", "CG": ".SZ", "TB": ".BK", "MK": ".KL", "IJ": ".JK", "PM": ".PS",
    "CN": ".TO", "CT": ".TO", "CV": ".V", "BZ": ".SA", "MM": ".MX", "AR": ".BA", "CI": ".SN",
    "SJ": ".JO", "TI": ".IS", "DU": ".AE", "DH": ".AD", "AB": ".SR", "QD": ".QA", "KK": ".KW",
    "TA": ".TA", "EY": ".CA",
}
# the ISIN's first two letters are the issuer's country: that country's exchange is home
HOME = {"US": "", "IN": ".NS", "GB": ".L", "DE": ".DE", "FR": ".PA", "NL": ".AS", "CH": ".SW", "IT": ".MI",
        "ES": ".MC", "BE": ".BR", "PT": ".LS", "DK": ".CO", "SE": ".ST", "NO": ".OL", "FI": ".HE", "AT": ".VI",
        "IE": ".L", "PL": ".WA", "JP": ".T", "HK": ".HK", "AU": ".AX", "NZ": ".NZ", "SG": ".SI", "KR": ".KS",
        "TW": ".TW", "CN": ".SS", "TH": ".BK", "MY": ".KL", "ID": ".JK", "PH": ".PS", "CA": ".TO", "BR": ".SA",
        "MX": ".MX", "AR": ".BA", "CL": ".SN", "ZA": ".JO", "TR": ".IS", "AE": ".AE", "SA": ".SR", "QA": ".QA",
        "KW": ".KW", "IL": ".TA", "EG": ".CA"}
NAMES = {"": "US", ".NS": "NSE", ".BO": "BSE", ".L": "LSE", ".DE": "XETRA", ".PA": "Paris", ".AS": "Amsterdam",
         ".SW": "SIX", ".MI": "Milan", ".MC": "Madrid", ".T": "Tokyo", ".HK": "Hong Kong", ".AX": "ASX",
         ".TO": "Toronto", ".SA": "B3", ".AE": "DFM", ".SI": "Singapore", ".KS": "Korea", ".TW": "Taiwan",
         ".SS": "Shanghai", ".SZ": "Shenzhen", ".JO": "JSE", ".ST": "Stockholm", ".CO": "Copenhagen"}


def is_isin(text):
    return bool(ISIN.match((text or "").strip().upper()))


def _read():
    try:
        with open(CACHE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _write(d):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    os.replace(tmp, CACHE_PATH)


def lookup(isin):
    """Listings for one ISIN, as search hits: symbol (the free feed's), name, exch, type.
    An empty list when OpenFIGI has nothing or does not answer."""
    isin = (isin or "").strip().upper()
    if not is_isin(isin):
        return []
    with _lock:
        cache = _read()
        hit = cache.get(isin)
    if hit and time.time() - hit.get("at", 0) < 90 * 86400:
        return hit["hits"]
    hits = []
    try:
        r = requests.post("https://api.openfigi.com/v3/mapping", json=[{"idType": "ID_ISIN", "idValue": isin}],
                          timeout=12, headers={"Content-Type": "application/json", "User-Agent": "greeksoup-desk"})
        if r.status_code == 200:
            rows = ((r.json() or [{}])[0] or {}).get("data") or []
            seen = set()
            for x in rows:
                if x.get("marketSector") not in ("Equity", None):
                    continue
                code = x.get("exchCode") or ""
                if code not in SUFFIX:
                    continue
                suffix = SUFFIX[code]
                # Bloomberg writes BP/ and AAPL* where the exchange writes BP and AAPL
                ticker = re.sub(r"[/*]", "", (x.get("ticker") or "")).replace(" ", "-")
                if not ticker:
                    continue
                sym = ticker + suffix
                if sym in seen:
                    continue
                seen.add(sym)
                hits.append({"symbol": sym, "name": x.get("name") or "", "exch": NAMES.get(suffix, code),
                             "type": "EQUITY", "isin": isin})
            # the issuer's home exchange first, so the first hit is the one to price
            home = HOME.get(isin[:2])
            def _rank(h):
                sfx = "." + h["symbol"].rsplit(".", 1)[1] if "." in h["symbol"] else ""
                return 0 if sfx == home else (1 if sfx in (".NS", "", ".L", ".DE", ".T", ".HK") else 2)
            hits.sort(key=_rank)
    except requests.RequestException:
        return (hit or {}).get("hits", [])
    if hits or r.status_code == 200:
        with _lock:
            cache = _read()
            cache[isin] = {"at": time.time(), "hits": hits}
            if len(cache) > 2000:
                cache = dict(sorted(cache.items(), key=lambda kv: kv[1].get("at", 0))[-1500:])
            _write(cache)
    return hits
