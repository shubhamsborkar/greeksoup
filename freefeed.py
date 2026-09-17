"""Keyless fallbacks for the US pages, from Yahoo Finance's public endpoints.

Used whenever FMP_API_KEY is empty, and as the backstop when the feed fails.
Two endpoints: the chart API (quote + candles, no login of any kind) and the
quoteSummary API (profile, estimates, earnings dates), which needs a session
cookie and a "crumb" that Yahoo hands out freely but rate-limits. Everything
here returns an empty shape instead of raising, so a page degrades instead of
dying. Yahoo's endpoints are unofficial and can change without notice.
"""
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

# Yahoo throttles by the pair (address, browser string), verified 16 September 2026: the same
# request answered 429 with one string and 200 with another from the same computer. So the
# desk keeps a few ordinary browser strings, and when one is throttled it moves to the next
# and stays there, which keeps a reader's desk answering through a burst.
UAS = [
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0"},
]
_ua = {"i": 0}
UA = UAS[0]                     # kept for callers that read it; _get uses the one that works
_Y = {"session": None, "crumb": None, "next_try": 0.0}
_lock = threading.Lock()
_throttle = {"until": 0.0}      # chart/search endpoints: five minutes off when every string is throttled


def _get(path, params):
    """GET against Yahoo: the browser string that last worked first, the others on a 429, the
    second host as a retry; five minutes off only when all of them are throttled."""
    if time.time() < _throttle["until"]:
        return None
    n = len(UAS)
    for k in range(n):
        idx = (_ua["i"] + k) % n
        for host in ("query1", "query2"):
            try:
                r = requests.get(f"https://{host}.finance.yahoo.com{path}", params=params, headers=UAS[idx], timeout=15)
            except Exception:  # noqa: BLE001
                continue
            if r.status_code == 200:
                _ua["i"] = idx
                return r
            if r.status_code != 429:
                break
    _throttle["until"] = time.time() + 300
    return None


def _num(x):
    if isinstance(x, dict):            # quoteSummary wraps values as {raw, fmt}
        x = x.get("raw")
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None       # drop NaN


def _auth():
    """Session cookie + crumb for quoteSummary. Backs off ten minutes when
    Yahoo throttles, and the callers then return empty shapes."""
    with _lock:
        if _Y["session"] and _Y["crumb"]:
            return True
        if time.time() < _Y["next_try"]:
            return False
        try:
            s = requests.Session()
            s.headers.update(UAS[_ua["i"]])
            s.get("https://fc.yahoo.com", timeout=10)
            crumb = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10).text
            if crumb and "<" not in crumb and len(crumb) < 40:
                _Y.update(session=s, crumb=crumb)
                return True
        except Exception:  # noqa: BLE001
            pass
        _Y.update(session=None, crumb=None, next_try=time.time() + 600)
        return False


def chart(symbol, rng="1y", interval="1d"):
    """-> (meta, rows). rows ascending, {date, price, o, h, l, v}. Keyless."""
    r = _get(f"/v8/finance/chart/{symbol}", {"range": rng, "interval": interval})
    try:
        res = (r.json().get("chart", {}).get("result") or [None])[0] if r else None
    except Exception:  # noqa: BLE001
        return {}, []
    if not res:
        return {}, []
    meta = res.get("meta") or {}
    ts = res.get("timestamp") or []
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    off = meta.get("gmtoffset") or 0
    rows = []
    for i, t in enumerate(ts):
        c = _num((q.get("close") or [None] * len(ts))[i])
        if c is None:
            continue
        d = datetime.fromtimestamp(t + off, tz=timezone.utc)
        rows.append({"date": d.strftime("%Y-%m-%d" if interval.endswith("d") or interval.endswith("wk") or interval.endswith("mo") else "%Y-%m-%d %H:%M"),
                     "price": c,
                     "o": _num((q.get("open") or [None] * len(ts))[i]),
                     "h": _num((q.get("high") or [None] * len(ts))[i]),
                     "l": _num((q.get("low") or [None] * len(ts))[i]),
                     "v": _num((q.get("volume") or [None] * len(ts))[i])})
    return meta, rows


def summary(symbol, modules):
    """quoteSummary modules for one symbol -> {module: {...}} or {}."""
    if not _auth():
        return {}
    try:
        r = _Y["session"].get(
            f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
            params={"modules": ",".join(modules), "crumb": _Y["crumb"]}, timeout=15)
        if r.status_code in (401, 403, 429):
            with _lock:
                _Y.update(session=None, crumb=None, next_try=time.time() + 600)
            return {}
        res = (r.json().get("quoteSummary", {}).get("result") or [None])[0]
        return res or {}
    except Exception:  # noqa: BLE001
        return {}


def _prev_close(meta, rows):
    """The last session's close: the daily bar before the latest one, and the
    meta's own field only when there is no second bar."""
    if len(rows) >= 2 and rows[-2].get("price") is not None:
        return tidy(rows[-2]["price"])
    return tidy(_num(meta.get("previousClose")) or _num(meta.get("chartPreviousClose")))


def tidy(x):
    """Yahoo's daily closes arrive as single-precision floats (1.15 comes back as
    1.1499999761, 118.16 as 118.16000366). Seven significant digits is all a
    single-precision number carries, so rounding there drops the noise and
    nothing else, and a flat day then reads flat instead of +0.00%."""
    if x is None or x == 0:
        return x
    return round(x, 6 - int(math.floor(math.log10(abs(x)))))


def quote(symbol):
    """One quote in the watch-grid schema (the shape the desk prices books with)."""
    meta, rows = chart(symbol, "5d", "1d")
    price = _num(meta.get("regularMarketPrice"))
    if price is None or price <= 0:
        return None
    # chartPreviousClose is the close before the RANGE (five sessions back here),
    # not the last session's; the previous close is the bar before the latest
    prev = _prev_close(meta, rows)
    last = rows[-1] if rows else {}
    return {
        "code": symbol, "exch": meta.get("exchangeName") or "US",
        "name": meta.get("longName") or meta.get("shortName"),
        "ltp": price, "prev": prev,
        "day_pct": ((price - prev) / prev * 100) if prev else None,
        "chg": (price - prev) if prev else None,
        "open": last.get("o"), "high": _num(meta.get("regularMarketDayHigh")) or last.get("h"),
        "low": _num(meta.get("regularMarketDayLow")) or last.get("l"),
        "ttq": _num(meta.get("regularMarketVolume")) or last.get("v"),
        "yhigh": _num(meta.get("fiftyTwoWeekHigh")), "ylow": _num(meta.get("fiftyTwoWeekLow")),
        "vs50": None, "vs200": None, "mcap": None,
        "ts": datetime.now().strftime("%H:%M:%S"),
    }


def ticker(symbol):
    """The ticker page's research view, keyless. Quote and candles from the
    chart API (always); profile, ratios, targets, analyst counts and the
    earnings record from quoteSummary when the crumb is available."""
    # Yahoo answers range=max at three-month steps whatever interval is asked,
    # so the daily record comes from the ten-year call and the years before it
    # from the quarterly one, joined where the daily record begins.
    meta, hist = chart(symbol, "10y", "1d")
    if hist:
        _, older = chart(symbol, "max", "3mo")
        first = hist[0]["date"]
        hist = [r for r in older if r["date"] < first] + hist
    price = _num(meta.get("regularMarketPrice"))
    if price is None or price <= 0:
        return {"symbol": symbol, "error": (f"The free feed has nothing for {symbol} right now. Either the name is spelt another way on the feed (a listing outside the US carries its exchange, HDFCBANK.NS, SHEL.L; a share class uses a dash, BRK-B), or the feed is resting after too many requests in a row and answers again in a few minutes."
                                            if time.time() >= _throttle["until"] else
                                            "The free feed is resting after too many requests in a row; it answers again in a few minutes. The watchlists keep their last prices meanwhile.")}
    imeta, intra = chart(symbol, "5d", "5m")
    prev = _num(imeta.get("previousClose")) or _prev_close(meta, hist)
    s = summary(symbol, ["summaryProfile", "summaryDetail", "defaultKeyStatistics",
                         "financialData", "recommendationTrend", "earningsHistory",
                         "calendarEvents"])
    prof, det, ks, fin = (s.get("summaryProfile") or {}, s.get("summaryDetail") or {},
                          s.get("defaultKeyStatistics") or {}, s.get("financialData") or {})
    trend = ((s.get("recommendationTrend") or {}).get("trend") or [{}])[0]
    quote_ = {
        "symbol": symbol, "price": price, "previousClose": prev,
        "change": (price - prev) if prev else None,
        "changePercentage": ((price - prev) / prev * 100) if prev else None,
        "open": (hist[-1].get("o") if hist else None),
        "dayHigh": _num(meta.get("regularMarketDayHigh")), "dayLow": _num(meta.get("regularMarketDayLow")),
        "yearHigh": _num(meta.get("fiftyTwoWeekHigh")), "yearLow": _num(meta.get("fiftyTwoWeekLow")),
        "volume": _num(meta.get("regularMarketVolume")), "avgVolume": _num(det.get("averageVolume")),
        "marketCap": _num(det.get("marketCap")), "exchange": meta.get("exchangeName"),
        "name": meta.get("longName") or meta.get("shortName"),
    }
    profile = {
        "companyName": meta.get("longName") or meta.get("shortName"),
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        "sector": prof.get("sector"), "industry": prof.get("industry"),
        "description": prof.get("longBusinessSummary"), "ceo": None,
        "fullTimeEmployees": prof.get("fullTimeEmployees"),
        "beta": _num(det.get("beta")), "lastDividend": _num(det.get("dividendRate")),
        "averageVolume": _num(det.get("averageVolume")),
    }
    mcap = _num(det.get("marketCap"))
    fcf = _num(fin.get("freeCashflow"))
    ratios = {
        "priceToEarningsRatioTTM": _num(det.get("trailingPE")),
        "priceToSalesRatioTTM": _num(det.get("priceToSalesTrailing12Months")),
        "priceToBookRatioTTM": _num(ks.get("priceToBook")),
        "priceToFreeCashFlowRatioTTM": (mcap / fcf) if (mcap and fcf and fcf > 0) else None,
        "priceToEarningsGrowthRatioTTM": _num(ks.get("pegRatio")),
        "dividendYieldTTM": _num(det.get("dividendYield")),
        "netProfitMarginTTM": _num(fin.get("profitMargins")), "grossProfitMarginTTM": _num(fin.get("grossMargins")),
        "operatingProfitMarginTTM": _num(fin.get("operatingMargins")),
        "debtToEquityRatioTTM": (_num(fin.get("debtToEquity")) / 100.0) if _num(fin.get("debtToEquity")) is not None else None,
        "currentRatioTTM": _num(fin.get("currentRatio")),
    }
    metrics = {
        "returnOnEquityTTM": _num(fin.get("returnOnEquity")), "returnOnAssetsTTM": _num(fin.get("returnOnAssets")),
        "returnOnInvestedCapitalTTM": None, "netDebtToEBITDATTM": None,
        "freeCashFlowYieldTTM": (fcf / mcap) if (mcap and fcf is not None) else None,
        "stockBasedCompensationToRevenueTTM": None, "researchAndDevelopementToRevenueTTM": None,
        "evToEBITDATTM": _num(ks.get("enterpriseToEbitda")), "marketCap": mcap,
        "enterpriseValueTTM": _num(ks.get("enterpriseValue")),
    }
    pt = {"lastQuarterAvgPriceTarget": _num(fin.get("targetMeanPrice")),
          "lastQuarterAvgPriceTargetHigh": _num(fin.get("targetHighPrice")),
          "lastQuarterAvgPriceTargetLow": _num(fin.get("targetLowPrice"))}
    grades = {"strongBuy": trend.get("strongBuy") or 0, "buy": trend.get("buy") or 0,
              "hold": trend.get("hold") or 0, "sell": trend.get("sell") or 0,
              "strongSell": trend.get("strongSell") or 0,
              "consensus": (fin.get("recommendationKey") or "").replace("_", " ").title()}
    earnings = []
    for h in ((s.get("earningsHistory") or {}).get("history") or []):
        d = h.get("quarter", {}).get("fmt") if isinstance(h.get("quarter"), dict) else h.get("quarter")
        earnings.append({"date": d, "epsActual": _num(h.get("epsActual")),
                         "epsEstimated": _num(h.get("epsEstimate")), "revenueActual": None})
    nxt = next_earnings_date(s)
    if nxt:
        earnings.append({"date": nxt, "epsActual": None, "epsEstimated": None, "revenueActual": None})
    earnings.sort(key=lambda e: e.get("date") or "", reverse=True)
    hist_desc = list(reversed(hist))
    days = sorted({p["date"][:10] for p in intra})
    return {
        "symbol": symbol, "quote": quote_, "profile": profile, "ratios": ratios,
        "metrics": metrics, "history": hist_desc,
        "intraday": {"1D": [p for p in intra if p["date"][:10] in days[-1:]],
                     "5D": [p for p in intra if p["date"][:10] in days[-5:]]},
        "news": [], "pt": pt, "grades": grades, "earnings": earnings,
        "insiders": [], "dividends": [],
        "source": "yahoo", "ts": datetime.now().strftime("%H:%M:%S"),
    }


def next_earnings_date(s):
    """'YYYY-MM-DD' of the next earnings date from a quoteSummary result, or None."""
    ev = (s.get("calendarEvents") or {}).get("earnings") or {}
    dates = ev.get("earningsDate") or []
    out = []
    for d in dates:
        raw = d.get("raw") if isinstance(d, dict) else d
        try:
            out.append(datetime.fromtimestamp(float(raw), tz=timezone.utc).strftime("%Y-%m-%d"))
        except (TypeError, ValueError):
            continue
    today = datetime.now().strftime("%Y-%m-%d")
    fut = [d for d in out if d >= today]
    return min(fut) if fut else None


def earnings(tag):
    """{symbol: 'held'|'watch'} -> the countdown rows the US desk renders."""
    def _one(sym):
        s = summary(sym, ["calendarEvents"])
        d = next_earnings_date(s) if s else None
        if not d:
            return None
        ev = (s.get("calendarEvents") or {}).get("earnings") or {}
        return {"symbol": sym, "date": d, "tag": tag[sym],
                "eps_est": _num(ev.get("earningsAverage")),
                "rev_est": _num(ev.get("revenueAverage"))}
    out = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(_one, list(tag)):
            if r:
                out.append(r)
    out.sort(key=lambda r: r["date"])
    return out


def search(q, limit=8):
    """Symbol search, keyless: [{code, name, exch}]."""
    r = _get("/v1/finance/search", {"q": q, "quotesCount": limit, "newsCount": 0})
    try:
        rows = (r.json().get("quotes") or []) if r else []
    except Exception:  # noqa: BLE001
        return []
    out = []
    for x in rows:
        if x.get("symbol") and x.get("quoteType") in (None, "EQUITY", "ETF", "INDEX", "MUTUALFUND"):
            out.append({"code": x["symbol"], "name": x.get("shortname") or x.get("longname") or "",
                        "exch": x.get("exchDisp") or x.get("exchange") or ""})
    return out[:limit]


# The three statements from Yahoo's fundamentals record, keyless and without the crumb, for
# any listed company in any market: four annual and four quarterly periods, fewer line items
# than a paid provider. Each Yahoo item is mapped to the field name the ticker page already
# reads, so the same table draws either source. A line Yahoo does not carry (gross profit for
# a bank) stays empty and the page skips it.
STATEMENT_ITEMS = {
    "inc": [("TotalRevenue", "revenue"), ("CostOfRevenue", "costOfRevenue"), ("GrossProfit", "grossProfit"),
            ("NetInterestIncome", "netInterestIncome"), ("TotalExpenses", "totalExpenses"),
            ("SellingGeneralAndAdministration", "sellingGeneralAndAdministrativeExpenses"),
            ("ResearchAndDevelopment", "researchAndDevelopmentExpenses"), ("OperatingExpense", "operatingExpenses"),
            ("OperatingIncome", "operatingIncome"), ("EBITDA", "ebitda"), ("ReconciledDepreciation", "depreciationAndAmortization"),
            ("InterestIncome", "interestIncome"), ("InterestExpense", "interestExpense"), ("PretaxIncome", "incomeBeforeTax"),
            ("TaxProvision", "incomeTaxExpense"), ("NetIncome", "netIncome"), ("BasicEPS", "eps"), ("DilutedEPS", "epsDiluted")],
    "bs": [("CashCashEquivalentsAndShortTermInvestments", "cashAndShortTermInvestments"), ("CashAndCashEquivalents", "cashAndCashEquivalents"),
           ("AccountsReceivable", "netReceivables"), ("Inventory", "inventory"), ("CurrentAssets", "totalCurrentAssets"),
           ("NetPPE", "propertyPlantEquipmentNet"), ("GoodwillAndOtherIntangibleAssets", "goodwillAndIntangibleAssets"),
           ("TotalAssets", "totalAssets"), ("CurrentDebt", "shortTermDebt"), ("LongTermDebt", "longTermDebt"), ("TotalDebt", "totalDebt"),
           ("NetDebt", "netDebt"), ("CurrentLiabilities", "totalCurrentLiabilities"), ("TotalLiabilitiesNetMinorityInterest", "totalLiabilities"),
           ("StockholdersEquity", "totalStockholdersEquity"), ("RetainedEarnings", "retainedEarnings")],
    "cf": [("NetIncomeFromContinuingOperations", "netIncome"), ("DepreciationAndAmortization", "depreciationAndAmortization"),
           ("StockBasedCompensation", "stockBasedCompensation"), ("ChangeInWorkingCapital", "changeInWorkingCapital"),
           ("OperatingCashFlow", "operatingCashFlow"), ("CapitalExpenditure", "capitalExpenditure"), ("FreeCashFlow", "freeCashFlow"),
           ("PurchaseOfBusiness", "acquisitionsNet"), ("InvestingCashFlow", "netCashProvidedByInvestingActivities"),
           ("NetIssuancePaymentsOfDebt", "netDebtIssuance"), ("RepurchaseOfCapitalStock", "commonStockRepurchased"),
           ("CashDividendsPaid", "netDividendsPaid"), ("FinancingCashFlow", "netCashProvidedByFinancingActivities"),
           ("ChangesInCash", "netChangeInCash")],
}


def statements(symbol, years=6):
    """-> {"inc_a", "inc_q", "bs_a", "bs_q", "cf_a", "cf_q", "currency"}; each list is oldest
    first, rows shaped {date, fiscalYear, period, <fields>}. Empty lists when Yahoo has nothing."""
    pairs = [(kind, y, f) for kind, items in STATEMENT_ITEMS.items() for y, f in items]
    types = ",".join(p + y for p in ("annual", "quarterly") for _, y, _ in pairs)
    now = int(time.time())
    try:
        r = requests.get(f"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}",
                         params={"type": types, "period1": now - years * 365 * 86400, "period2": now},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        res = (r.json().get("timeseries") or {}).get("result") or []
    except Exception:  # noqa: BLE001
        return {}
    by = {}     # (kind, period) -> {date -> row}
    currency = ""
    field_of = {(kind, y): f for kind, y, f in pairs}
    for x in res:
        t = (x.get("meta") or {}).get("type", [""])[0]
        per = "a" if t.startswith("annual") else "q"
        y = t[len("annual"):] if per == "a" else t[len("quarterly"):]
        for kind in STATEMENT_ITEMS:
            f = field_of.get((kind, y))
            if not f:
                continue
            for v in x.get(t) or []:
                d = v.get("asOfDate") or ""
                val = _num((v.get("reportedValue") or {}).get("raw"))
                if not d or val is None:
                    continue
                currency = currency or v.get("currencyCode") or ""
                row = by.setdefault((kind, per), {}).setdefault(d, {"date": d, "fiscalYear": d[:4], "period": "Q" + str((int(d[5:7]) - 1) // 3 + 1)})
                row[f] = val
    out = {"currency": currency}
    for kind in STATEMENT_ITEMS:
        for per in ("a", "q"):
            rows = sorted(by.get((kind, per), {}).values(), key=lambda r: r["date"])
            out[f"{kind}_{per}"] = rows[-4:] if per == "q" else rows[-6:]
    return out


# The economic calendar behind Yahoo's own calendar page: every country's prints with the
# consensus and the prior, in windows of a week, with the cookie and crumb the quote summary
# uses. Nothing here needs a key. Returns rows or [] when the feed is resting.
_ECON_KEYS = {"event": ("event", "eventName", "name"), "consensus": ("consensus", "forecast", "expected", "estimate"),
              "prior": ("prior", "previous"), "actual": ("actual",), "period": ("period", "forPeriod")}


def _pick(rec, keys):
    for k in keys:
        if rec.get(k) not in (None, ""):
            return rec.get(k)
    return None


def econ_calendar(days=60, high_only=False):
    if not _auth():
        return []
    out, seen = [], set()
    start = time.time()
    for k in range(0, days, 7):
        a = int((start + k * 86400) * 1000)
        b = int((start + min(k + 7, days) * 86400) * 1000)
        try:
            r = _Y["session"].get("https://query1.finance.yahoo.com/ws/screeners/v1/finance/calendar-events",
                                  params={"modules": "economicEvents", "startDate": a, "endDate": b, "countPerDay": 250,
                                          "economicEventsHighImportanceOnly": "true" if high_only else "false",
                                          "economicEventsRegionFilter": "", "lang": "en-US", "region": "US", "crumb": _Y["crumb"]},
                                  timeout=20)
        except Exception:  # noqa: BLE001
            break
        if r.status_code == 429:
            _Y.update(session=None, crumb=None, next_try=time.time() + 600)
            break
        if r.status_code != 200:
            break
        try:
            j = r.json()
        except ValueError:
            break
        # the records sit a few levels down; walk for every dict that names an event and a country
        stack = [j]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                if o.get("countryCode") and _pick(o, _ECON_KEYS["event"]) and o.get("eventTime"):
                    t = o.get("eventTime")
                    try:
                        t = float(t) / (1000.0 if float(t) > 1e11 else 1.0)
                    except (TypeError, ValueError):
                        continue
                    when = datetime.utcfromtimestamp(t)
                    key = (o["countryCode"], _pick(o, _ECON_KEYS["event"]), when.strftime("%Y-%m-%d"))
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({"date": when.strftime("%Y-%m-%d"), "time": when.strftime("%H:%M"), "country": o["countryCode"],
                                "event": str(_pick(o, _ECON_KEYS["event"])), "period": _pick(o, _ECON_KEYS["period"]) or "",
                                "estimate": _pick(o, _ECON_KEYS["consensus"]), "previous": _pick(o, _ECON_KEYS["prior"]),
                                "actual": _pick(o, _ECON_KEYS["actual"]), "high": bool(high_only or o.get("importance") in ("High", "high", 3))})
                else:
                    stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)
    out.sort(key=lambda r: (r["date"], r["time"]))
    return out
