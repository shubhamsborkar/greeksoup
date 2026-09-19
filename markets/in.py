"""India as a home market, from the public record: the NSE session, NIFTY 50 as
the benchmark, the exchange's results calendar and integrated filings, and the
three macro cards FRED does not carry well (the 10-year is on FRED with a lag;
the repo rate and CPI come from public pages). Any broker whose file says
region "in" (the two shipped Indian brokers, or one your agent writes) gets
all of it; nothing here needs a broker or a key."""

import json
import os
import re
import subprocess
import time
from datetime import datetime

import requests

import fred

META = {
    "id": "in",
    "label": "India",
    "currency": "INR", "symbol": "₹", "locale": "en-IN",
    "exchanges": ["NSE", "BSE"],
    "session_label": "NSE",
    "benchmark": "^NSEI", "benchmark_label": "NIFTY 50",
    "econ_country": "IN",
    "filings": "NSE integrated filings", "units": "₹ Cr",
}

_SUFFIX = {"NSE": ".NS", "BSE": ".BO"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(ROOT, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36")


def is_open(now=None):
    """NSE regular session, 09:15 to 15:30, in the computer's local time."""
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False
    hm = now.hour * 60 + now.minute
    return (9 * 60 + 15) <= hm <= (15 * 60 + 30)


def ysym(symbol, exch=None):
    """RELIANCE on NSE -> RELIANCE.NS; a symbol that already carries a Yahoo
    suffix is returned as it is."""
    s = (symbol or "").upper()
    if not s or "." in s:
        return s
    return s + _SUFFIX.get((exch or "NSE").upper(), ".NS")


def from_ysym(ysym):
    """HDFCBANK.NS -> ("HDFCBANK", "NSE"); None when the suffix is not this market's."""
    s = (ysym or "").upper()
    for exch, suf in _SUFFIX.items():
        if s.endswith(suf) and len(s) > len(suf):
            return s[:-len(suf)], exch
    return None


# ---- the exchange's public API (needs a cookie warm-up) ---------------------
_nse = {"session": None, "warmed": 0.0}


def _nse_get(path):
    """NSE blocks bare API hits; a homepage visit first sets the cookies it
    checks. Session reused ~10 min, rebuilt on any failure."""
    now = time.time()
    s = _nse["session"]
    if s is None or now - _nse["warmed"] > 600:
        s = requests.Session()
        s.headers.update({"User-Agent": _UA, "Accept": "application/json"})
        try:
            s.get("https://www.nseindia.com", timeout=15)
        except Exception:  # noqa: BLE001
            return None
        _nse.update(session=s, warmed=now)
    try:
        r = s.get(f"https://www.nseindia.com/api/{path}", timeout=15)
        if r.status_code != 200:
            _nse["session"] = None
            return None
        return r.json()
    except Exception:  # noqa: BLE001
        _nse["session"] = None
        return None


def results_calendar(symbols):
    """Upcoming board meetings with a results purpose for each NSE symbol.
    Per-symbol calls, politely paced; the caller caches half a day. A symbol
    with no NSE listing is counted in "skipped", not hidden."""
    today = datetime.now().date()
    rows, skipped = [], 0
    for sym in symbols:
        if not sym:
            skipped += 1
            continue
        events = _nse_get(f"event-calendar?index=equities&symbol={sym}") or []
        best = None
        for e in events:
            if "result" not in (e.get("purpose") or "").lower():
                continue
            try:
                d = datetime.strptime(e.get("date") or "", "%d-%b-%Y").date()
            except ValueError:
                continue
            if d >= today and (best is None or d < best[0]):
                best = (d, e)
        if best:
            d, e = best
            rows.append({"symbol": sym, "company": (e.get("company") or "").title(),
                         "date": d.strftime("%Y-%m-%d"), "purpose": e.get("purpose")})
        time.sleep(0.4)
    rows.sort(key=lambda r: r["date"])
    return {"rows": rows, "skipped": skipped}


def fundamentals(symbol):
    """Quarterly results, shareholding and the Reg 30 stream from the
    exchange's integrated filings. None when the exchange is unreachable."""
    import nse_fund
    return nse_fund.build(symbol)


# ---- macro: the 10-year from FRED, the repo rate and CPI from public pages --
def macro_series():
    return [("INDIRLTLT01STM", "India 10Y yield", "%", "India",
             lambda: fred.csv("INDIRLTLT01STM")),
            ("INCPI_MOSPI", "India CPI YoY", "%", "India", _cpi)]


def macro_cards():
    repo = _repo()
    if not repo:
        return []
    hist = repo.get("history") or []
    delta = (hist[-1][1] - hist[-2][1]) if len(hist) >= 2 else None
    return [{"id": "REPO_RBI", "label": "RBI repo rate", "unit": "%",
             "group": "India", "value": repo["rate"],
             "date": repo.get("date", ""), "delta": delta,
             "spark": [v for _, v in hist][-40:],
             "full": [[d, v] for d, v in hist]}]


_REPO_PATH = os.path.join(CACHE_DIR, "india_repo.json")


def _repo():
    """Repo rate with its change history, from BankBazaar's history table;
    the current rate from Trading Economics' sentence as the fallback. The
    last good data persists on disk, so a failed scrape degrades to dated,
    never to nothing."""
    try:
        with open(_REPO_PATH) as fh:
            prev = json.load(fh)
    except (OSError, ValueError):
        prev = None
    if prev and time.time() - prev.get("at", 0) < 24 * 3600:
        return prev
    hist = []
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", "25", "-A", _UA,
             "https://www.bankbazaar.com/home-loan/repo-rate.html"],
            capture_output=True, text=True, timeout=30)
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", r.stdout, re.S)]
        for i, c in enumerate(cells):
            m = re.match(r"^(\d{1,2}\s+\w+\s+\d{4})$", c)
            if m and i + 1 < len(cells):
                rate = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*%$", cells[i + 1])
                if rate:
                    try:
                        d = datetime.strptime(m.group(1), "%d %B %Y")
                        hist.append((d.strftime("%Y-%m-%d"), float(rate.group(1))))
                    except ValueError:
                        pass
    except Exception:  # noqa: BLE001
        pass
    hist = sorted(set(hist))
    if hist:
        data = {"rate": hist[-1][1], "date": hist[-1][0], "at": time.time(), "history": hist}
        with open(_REPO_PATH, "w") as fh:
            json.dump(data, fh)
        return data
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", "25", "-A", _UA,
             "https://tradingeconomics.com/india/interest-rate"],
            capture_output=True, text=True, timeout=30)
        m = re.search(r"benchmark interest rate in india was last recorded at\s*"
                      r"([0-9]+(?:\.[0-9]+)?)\s*percent", r.stdout, re.I)
        if m:
            data = {"rate": float(m.group(1)), "at": time.time(),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "history": (prev or {}).get("history", [])}
            with open(_REPO_PATH, "w") as fh:
                json.dump(data, fh)
            return data
    except Exception:  # noqa: BLE001
        pass
    return prev


_MONTH_NUM = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def _cpi():
    """All-India headline CPI YoY from MOSPI's public API (keyless). The API
    still serves the 2012-base series, which ended December 2025 when India
    rebased to 2024, so the card is history-complete and its latest print is
    dated on the card. MOSPI needs legacy TLS renegotiation, which python's
    OpenSSL refuses; curl handles it."""
    series = []
    for year in range(2014, 2026):
        url = ("https://api.mospi.gov.in/api/cpi/getCPIIndex?base_year=2012"
               f"&series=Current&year={year}&sector_code=3&group_code=0"
               "&state_code=99&limit=20")
        try:
            r = subprocess.run(["curl", "-s", "-m", "25", "-A", "Mozilla/5.0", url],
                               capture_output=True, text=True, timeout=30)
            rows = json.loads(r.stdout).get("data", [])
        except Exception:  # noqa: BLE001
            rows = []
        for row in rows:
            try:
                infl = float(row.get("inflation"))
            except (TypeError, ValueError):
                continue
            mn = _MONTH_NUM.get(row.get("month"))
            if mn:
                series.append((f"{year}-{mn:02d}-01", infl))
        time.sleep(0.3)
    return sorted(set(series))


# ---- the local layer of the Commodities board, with no broker at all ----------
def commodities_local(cards):
    """India's own prices beside the global benchmarks, keyless: the benchmark mandi
    for each crop the board carries (Indore wheat and soybean, Davangere maize, Raichur
    kapas, Muzaffarnagar gur) from the Indian Mandi Prices API, and Kottayam RSS4 from
    the Rubber Board's daily sheet. A broker file that serves MCX adds its futures on
    top. Returns True when anything was attached."""
    import local_in
    try:
        mandi = local_in.mandi_prices()
    except Exception:  # noqa: BLE001
        mandi = {}
    try:
        rb = local_in.rubber_board()
    except Exception:  # noqa: BLE001
        rb = None
    hit = False
    for c in cards:
        loc = list(c.get("local") or [])
        have = {l.get("short") for l in loc}
        m = mandi.get(c["id"])
        if m and m["short"] not in have:
            loc.append(m)
            hit = True
        if c["id"] == "rubber" and rb and rb.get("grades", {}).get("RSS4") and "Kottayam RSS4" not in have:
            g = rb["grades"]["RSS4"]
            loc.append({"kind": "local", "tag": "INDIA", "label": f"Kottayam RSS4 · Rubber Board {rb.get('date', '')}",
                        "short": "Kottayam RSS4", "note": "the domestic grade Indian tyre makers buy",
                        "detail": "India domestic", "level": g["inr_per_kg"], "unit": "₹/kg", "usc_per_kg": g["usc_per_kg"],
                        "stale": rb.get("stale", False), "ts": rb.get("date")})
            hit = True
        if loc:
            c["local"] = loc
    return hit

