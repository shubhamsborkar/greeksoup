"""The Calendar: every dated event on every name the reader holds or watches,
from the free record, kept fresh by the desk on its own.

For each name: the next results date and the dividend dates from Yahoo's free
summary (any exchange), and for a US listing the filings that landed at the
SEC in the last weeks (10-K, 10-Q, 8-K, the proxy, 13D and 13G, from EDGAR's
own index). The home market's own results calendar and the macro calendar,
when the desk holds them, join the same list. No key is needed for any of it;
a data provider adds nothing here that the free record does not already carry.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import re
import time

import requests

import freefeed
import sec_form4

_NASDAQ_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36",
              "Accept": "application/json", "Accept-Language": "en-US,en;q=0.9"}

TTL = 6 * 3600
AHEAD_DAYS = 90            # how far ahead the list looks
BACK_DAYS = 30             # how far back landed filings are kept
FORMS = {"10-K": "Annual report", "10-Q": "Quarterly report", "8-K": "Current report", "20-F": "Annual report (foreign filer)",
         "6-K": "Report of a foreign filer", "DEF 14A": "Proxy statement", "SC 13D": "13D: an active holder above 5%",
         "SC 13D/A": "13D amended", "SC 13G": "13G: a passive holder above 5%", "SC 13G/A": "13G amended",
         "10-K/A": "Annual report, amended", "10-Q/A": "Quarterly report, amended", "S-1": "Registration (an offering)",
         "424B4": "Prospectus (an offering priced)", "S-3": "Shelf registration", "8-K/A": "Current report, amended"}


def _date(x):
    """A Yahoo {raw, fmt} or epoch -> 'YYYY-MM-DD', else None."""
    if isinstance(x, dict):
        x = x.get("raw")
    try:
        return datetime.fromtimestamp(float(x), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def yahoo_events(sym):
    """The dated events Yahoo's free summary carries for one symbol."""
    s = freefeed.summary(sym, ["calendarEvents"])
    if not s:
        # an empty answer is "no events" when the feed is up, and "ask again" when
        # it has just said too many requests and backed off
        return None if freefeed._Y.get("next_try", 0) > time.time() else []
    ev = s.get("calendarEvents") or {}
    earn = ev.get("earnings") or {}
    out = []
    dates = sorted({d for d in (_date(x) for x in (earn.get("earningsDate") or [])) if d})
    if dates:
        eps = freefeed._num(earn.get("earningsAverage"))
        rev = freefeed._num(earn.get("revenueAverage"))
        detail = []
        if eps is not None:
            detail.append(f"EPS expected {eps:.2f}")
        if rev:
            detail.append("revenue expected " + (f"{rev / 1e9:.2f} bn" if rev >= 1e9 else f"{rev / 1e6:.0f} mn"))
        window = f" (between {dates[0]} and {dates[-1]})" if len(dates) > 1 else ""
        out.append({"date": dates[0], "kind": "results", "what": "Results" + window, "detail": ", ".join(detail),
                    "window_end": dates[-1] if len(dates) > 1 else ""})
    exd = _date(ev.get("exDividendDate"))
    if exd:
        out.append({"date": exd, "kind": "ex_dividend", "what": "Goes ex-dividend", "detail": ""})
    pay = _date(ev.get("dividendDate"))
    if pay:
        out.append({"date": pay, "kind": "dividend", "what": "Dividend paid", "detail": ""})
    return out


def _mdy(text):
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text or "")
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else None


def nasdaq_events(sym):
    """The same events for a US listing from Nasdaq's own site, no key: the
    expected results date and the dividend dates. The second source, for the
    days Yahoo's free feed says too many requests."""
    out = []
    try:
        r = requests.get(f"https://api.nasdaq.com/api/analyst/{sym}/earnings-date", headers=_NASDAQ_UA, timeout=15)
        text = ((r.json().get("data") or {}).get("reportText") or "") if r.status_code == 200 else ""
        d = _mdy(text)
        if d:
            out.append({"date": d, "kind": "results", "what": "Results (expected)", "detail": "date estimated from past reporting dates until the company confirms it"})
    except Exception:  # noqa: BLE001
        pass
    try:
        r = requests.get(f"https://api.nasdaq.com/api/quote/{sym}/dividends", params={"assetclass": "stocks"}, headers=_NASDAQ_UA, timeout=15)
        data = (r.json().get("data") or {}) if r.status_code == 200 else {}
        exd, pay = _mdy(data.get("exDividendDate") or ""), _mdy(data.get("dividendPaymentDate") or "")
        if exd:
            out.append({"date": exd, "kind": "ex_dividend", "what": "Goes ex-dividend", "detail": (data.get("annualizedDividend") and f"annual dividend {data['annualizedDividend']}") or ""})
        if pay:
            out.append({"date": pay, "kind": "dividend", "what": "Dividend paid", "detail": ""})
    except Exception:  # noqa: BLE001
        pass
    return out or None


def edgar_filings(sym, back_days=BACK_DAYS):
    """Filings that landed at the SEC for a US listing in the last weeks, from
    EDGAR's own submissions index; [] when the symbol has no CIK."""
    cik, _ = sec_form4.cik_map().get(sym.upper(), (None, None))
    if not cik:
        return []
    try:
        r = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=sec_form4.UA, timeout=20)
        if r.status_code != 200:
            return []
        rec = (r.json().get("filings") or {}).get("recent") or {}
    except Exception:  # noqa: BLE001
        return []
    since = (datetime.now() - timedelta(days=back_days)).strftime("%Y-%m-%d")
    forms, dates, accs, docs, descs = (rec.get(k) or [] for k in ("form", "filingDate", "accessionNumber", "primaryDocument", "primaryDocDescription"))
    out = []
    for form, date, acc, doc, desc in zip(forms, dates, accs, docs, descs):
        if date < since or form not in FORMS:
            continue
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}" if doc else f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
        desc = "" if (desc or "").upper().replace("FORM ", "").strip() == form.upper() else (desc or "")
        out.append({"date": date, "kind": "filing", "form": form, "what": FORMS[form], "detail": desc, "url": url})
    return out


def build(universe, home_results=None, macro=None):
    """universe: {yahoo_symbol: {"symbol": shown, "name": ..., "tag": "held"|"watch"}}.
    Returns the upcoming list, the landed filings, the macro rows and the notes."""
    today = datetime.now().strftime("%Y-%m-%d")
    horizon = (datetime.now() + timedelta(days=AHEAD_DAYS)).strftime("%Y-%m-%d")
    upcoming, landed, failed = [], [], []

    def _one(ysym):
        info = universe[ysym]
        us = "." not in ysym and not ysym.startswith("^")
        evs = yahoo_events(ysym)
        if evs is None and us:
            evs = nasdaq_events(ysym)
        if evs is None:
            failed.append(ysym)
            evs = []
        fil = edgar_filings(ysym) if ("." not in ysym and not ysym.startswith("^")) else []
        return ysym, info, evs, fil

    with ThreadPoolExecutor(max_workers=3) as ex:
        for ysym, info, evs, fil in ex.map(_one, list(universe)):
            base = {"symbol": info["symbol"], "ysym": ysym, "name": info.get("name") or "", "tag": info["tag"]}
            for e in evs:
                if today <= e["date"] <= horizon:
                    upcoming.append(base | e)
            for f in fil:
                landed.append(base | f)
    seen = set()
    have_results = {(u["symbol"], u["kind"]) for u in upcoming}
    for r in (home_results or []):
        sym = (r.get("code") or r.get("symbol") or "").upper()
        date = (r.get("date") or "")[:10]
        if not sym or not date or not (today <= date <= horizon) or (sym, "results") in have_results:
            continue
        if (sym, date) in seen:
            continue
        seen.add((sym, date))
        upcoming.append({"symbol": sym, "ysym": sym, "name": r.get("company") or r.get("name") or "", "tag": r.get("tag") or "watch",
                         "date": date, "kind": "results", "what": "Results (board meeting)",
                         "detail": r.get("purpose") or ""})
    upcoming.sort(key=lambda r: (r["date"], r["tag"] != "held", r["symbol"]))
    landed.sort(key=lambda r: (r["date"], r["symbol"]), reverse=True)
    macro_rows = []
    for r in (macro or []):
        d = (r.get("date") or "")[:10]
        if d and today <= d <= horizon:
            macro_rows.append({"date": d, "time": (r.get("date") or "")[11:16], "country": r.get("country") or "",
                               "event": r.get("event") or "", "impact": r.get("impact") or "",
                               "estimate": r.get("estimate"), "previous": r.get("previous")})
    out = {"upcoming": upcoming, "landed": landed, "macro": macro_rows,
           "names": len(universe), "held": sum(1 for v in universe.values() if v["tag"] == "held"),
           "failed": sorted(failed)[:20], "ahead_days": AHEAD_DAYS, "back_days": BACK_DAYS,
           "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}
    if failed:
        out["_ttl"] = 900       # a feed said no to some names: the desk tries again in fifteen minutes, not six hours
    return out
