"""Shikshan Nivesh Data (shikshannivesh.com/data), the desk's main source for company financials.

The three statements, the ratio history, the segment mix and the dividend per share by year on the
ticker page, read from SEC filings in the provider's standard template, and the company list the
Peers tab picks from (every covered company with its SEC industry). Every other screen keeps its
free public source (prices from Yahoo, short interest from FINRA, insiders and the calendar from
the SEC), so the reader's key is spent only when a company's financials are opened: three calls a
company (statements, ratios, segments), kept twelve hours by the desk's own cache, plus one call a
day for the company list. The free plan's 250 calls a day is about eighty companies. The Peers tab,
only when it is opened, spends one call for each company in the table, and keeps each a week.

The rows come back in the shape the ticker page already draws (the field names it reads from
the first provider), newest first. Cash spent (capital expenditure, acquisitions, buybacks,
dividends) is negative, the way the page shows money going out.
"""
import os
import re
from datetime import date

import requests

META = {"label": "Shikshan Nivesh Data", "docs": "https://shikshannivesh.com/data/developers",
        "plans": "https://shikshannivesh.com/data/plans"}
BASE = "https://shikshannivesh.com/api/v1"
ENV_KEY = "SN_API_KEY"

# the provider's standard line ids -> the ticker page's fields
FIELDS = {
    "IS": {"rev": "revenue", "cogs": "costOfRevenue", "gp": "grossProfit", "opex": "operatingExpenses",
           "sga": "sellingGeneralAndAdministrativeExpenses", "rnd": "researchAndDevelopmentExpenses",
           "opinc": "operatingIncome", "ebitda": "ebitda", "da": "depreciationAndAmortization",
           "int_exp": "interestExpense", "int_inc": "interestIncome", "int_net": "netInterestIncome",
           "pretax": "incomeBeforeTax", "tax": "incomeTaxExpense", "ni": "netIncome",
           "eps_basic": "eps", "eps_dil": "epsDiluted",
           "shares_basic": "weightedAverageShsOut", "shares_dil": "weightedAverageShsOutDil"},
    "BS": {"cash_sti": "cashAndShortTermInvestments", "cash": "cashAndCashEquivalents", "recv": "netReceivables",
           "inv": "inventory", "ca": "totalCurrentAssets", "ppe": "propertyPlantEquipmentNet",
           "intang_total": "goodwillAndIntangibleAssets", "assets": "totalAssets", "st_debt": "shortTermDebt",
           "ltd": "longTermDebt", "total_debt": "totalDebt", "net_debt": "netDebt",
           "cl": "totalCurrentLiabilities", "liabilities": "totalLiabilities",
           "equity": "totalStockholdersEquity", "re": "retainedEarnings", "shares_out": "sharesOutstanding"},
    "CF": {"cf_ni": "netIncome", "cf_da": "depreciationAndAmortization", "cf_sbc": "stockBasedCompensation",
           "cf_wc": "changeInWorkingCapital", "cfo": "operatingCashFlow", "capex": "capitalExpenditure",
           "fcf": "freeCashFlow", "acq": "acquisitionsNet", "cfi": "netCashProvidedByInvestingActivities",
           "net_debt_flow": "netDebtIssuance", "buyback": "commonStockRepurchased", "div_paid": "netDividendsPaid",
           "cff": "netCashProvidedByFinancingActivities", "net_change": "netChangeInCash"},
}
# a receivables total the filing does not give falls back to trade receivables
FALLBACK = {"BS": {"netReceivables": "ar"}}
KIND = {"IS": "inc", "BS": "bs", "CF": "cf"}


def key():
    return os.getenv(ENV_KEY, "").strip()


def _get(path, **params):
    """(json, None) or (None, {"kind", "message"}). Never raises."""
    k = key()
    if not k:
        return None, {"kind": "no_key", "message": "No Shikshan Nivesh Data key is saved on Settings."}
    try:
        r = requests.get(BASE + path, params=params, headers={"X-API-Key": k}, timeout=25)
    except requests.RequestException:
        return None, {"kind": "network", "message": "Shikshan Nivesh Data did not answer just now."}
    if r.status_code == 200:
        try:
            return r.json(), None
        except ValueError:
            return None, {"kind": "network", "message": "Shikshan Nivesh Data sent an answer the desk could not read."}
    try:
        err = (r.json() or {}).get("error") or {}
    except ValueError:
        err = {}
    code = err.get("code") or ""
    kind = {401: "key", 404: "missing", 429: "limit" if code == "daily_limit" else "busy"}.get(r.status_code, "network")
    # the provider's own words, except where they speak to a developer (an address to call)
    said = err.get("message") or f"Shikshan Nivesh Data answered {r.status_code}."
    if kind == "missing":
        said = "Shikshan Nivesh Data does not cover this company yet."
    return None, {"kind": kind, "message": said}


def _fiscal(d, fy_end_month, quarterly):
    """(fiscalYear, period) for a period ending on d, the way the page labels columns."""
    if not quarterly:
        return str(d.year), "FY"
    after = (d.month - fy_end_month) % 12          # months past the fiscal year end; 0 is the year end itself
    q = 4 if after == 0 else (after - 1) // 3 + 1
    return str(d.year if d.month <= fy_end_month else d.year + 1), f"Q{q}"


def _rows(block, kind, fy_end_month, quarterly, currency, limit):
    periods = block.get("periods") or []
    lines = {ln.get("id"): ln for ln in block.get("lines") or []}
    out = []
    for p in sorted(periods, reverse=True)[:limit]:
        try:
            d = date.fromisoformat(p[:10])
        except ValueError:
            continue
        fy, per = _fiscal(d, fy_end_month, quarterly)
        row = {"date": p[:10], "fiscalYear": fy, "period": per, "reportedCurrency": currency}
        for lid, field in FIELDS[kind].items():
            ln = lines.get(lid)
            v = (ln or {}).get("values", {}).get(p)
            if v is None and field in FALLBACK.get(kind, {}):
                v = (lines.get(FALLBACK[kind][field]) or {}).get("values", {}).get(p)
            if v is None:
                continue
            if kind == "CF" and (ln or {}).get("sign") == "-":
                v = -v                       # money going out reads negative on the page
            row[field] = v
        out.append(row)
    return out


def statements(symbol, years=6, quarters=8):
    """{"inc_a", "inc_q", "bs_a", "bs_q", "cf_a", "cf_q", "currency", "record"} newest first, or
    {"error": {...}}. One call: both periods, the standard template."""
    j, err = _get(f"/companies/{symbol}/financials", basis="standard")
    if err:
        return {"error": err}
    currency = j.get("currency") or "USD"
    annual, quarterly = j.get("annual") or {}, j.get("quarterly") or {}
    ann_periods = sorted((annual.get("IS") or {}).get("periods") or [])
    fy_end = int(ann_periods[-1][5:7]) if ann_periods else 12
    out = {"currency": currency, "record": (j.get("access") or {}).get("record") or ""}
    for kind, short in KIND.items():
        out[f"{short}_a"] = _rows(annual.get(kind) or {}, kind, fy_end, False, currency, years)
        out[f"{short}_q"] = _rows(quarterly.get(kind) or {}, kind, fy_end, True, currency, quarters)
    if not (out["inc_a"] or out["bs_a"]):
        return {"error": {"kind": "missing", "message": "Shikshan Nivesh Data does not cover this company yet."}}
    return out


def segments(symbol, years=6):
    """{"seg_p": [...], "seg_g": [...]} in the page's shape ({fiscalYear, period, data}), or {}."""
    j, err = _get(f"/companies/{symbol}/segments")
    if err:
        return {}
    segs = j.get("segments") or {}

    def shape(group):
        g = segs.get(group) or {}
        cols = []
        for y in sorted(g.get("years") or [])[-years:]:
            data = {r["label"]: r["values"].get(y) for r in g.get("rows") or []
                    if r.get("label") and isinstance(r.get("values"), dict) and r["values"].get(y) is not None}
            if data:
                cols.append({"date": y, "fiscalYear": int(y[:4]), "period": "FY", "data": data})
        return cols
    return {"seg_p": shape("product") or shape("business"), "seg_g": shape("geography")}


# the provider's figure ids -> (the Ratios tab's field, divide by 100 when it is a percent)
RATIOS = {"gross_margin": ("grossProfitMargin", True), "operating_margin": ("operatingProfitMargin", True),
          "ebitda_margin": ("ebitdaMargin", True), "net_margin": ("netProfitMargin", True),
          "fcf_ocf": ("freeCashFlowOperatingCashFlowRatio", False), "dps": ("dividendPerShare", False),
          "payout": ("dividendPayoutRatio", True), "asset_turnover": ("assetTurnover", False),
          "current_ratio": ("currentRatio", False), "quick_ratio": ("quickRatio", False),
          "debt_equity": ("debtToEquityRatio", False)}
METRICS = {"roe": ("returnOnEquity", True), "roic": ("returnOnInvestedCapital", True), "roa": ("returnOnAssets", True),
           "roce": ("returnOnCapitalEmployed", True), "net_debt_ebitda": ("netDebtToEBITDA", False)}


def ratios(symbol, years=6):
    """{"ratios": [...], "metrics": [...]} newest first in the Ratios tab's shape, or {}. One call,
    asking only for the figures the tab shows. Nothing worked out from a share price is served."""
    j, err = _get(f"/companies/{symbol}/figures", period="annual", ids=",".join(list(RATIOS) + list(METRICS)))
    if err:
        return {}
    by_id = {f.get("id"): f.get("annual") or {} for f in j.get("figures") or []}
    labels = {p.get("end"): p.get("label") or "" for p in (j.get("periods") or {}).get("annual") or []}
    ends = sorted({e for vals in by_id.values() for e in vals}, reverse=True)[:years]

    def rows(table):
        out = []
        for e in ends:
            fy = re.sub(r"\D", "", labels.get(e, "")) or e[:4]
            row = {"date": e, "fiscalYear": fy}
            for fid, (field, pct) in table.items():
                v = by_id.get(fid, {}).get(e)
                if v is not None:
                    row[field] = v / 100 if pct else v
            out.append(row)
        return out
    return {"ratios": rows(RATIOS), "metrics": rows(METRICS)} if ends else {}


def company(symbol):
    """One company's latest figures (the provider's TTM metrics: revenue, profit, margins, shares,
    debt, dividend per share), or None. One call; the Peers tab keeps it a week."""
    j, err = _get(f"/companies/{symbol}")
    if err:
        return None
    co = j.get("company") or {}
    return {"name": co.get("name") or "", "currency": co.get("currency") or "", **(j.get("metrics") or {})}


def companies():
    """Every covered company: [{symbol, name, exchange, industry, index, ...}], or [] on any refusal.
    One call; the server keeps it a day."""
    j, err = _get("/companies")
    if err:
        return []
    return [c for c in j.get("companies") or [] if c.get("symbol")]


# the index a company sits in, biggest first: the order peers are picked in before their sizes are known
INDEX_RANK = {"S&P 500": 0, "S&P MidCap 400": 1, "S&P SmallCap 600": 2}


def peers(symbol, listing, n=10):
    """(industry, [symbols]) for the companies in the same SEC industry as symbol, up to n, the
    largest index first; ("", []) when the company is alone in its industry or not covered."""
    norm = lambda c: " ".join((c.get("industry") or "").split())  # noqa: E731  (the list has a few double spaces)
    me = next((c for c in listing if c["symbol"] == symbol), None)
    ind = norm(me or {})
    if not ind:
        return "", []
    same = [c for c in listing if c["symbol"] != symbol and norm(c).lower() == ind.lower()]
    same.sort(key=lambda c: (INDEX_RANK.get(c.get("index") or "", 3), c["symbol"]))
    return ind, [c["symbol"] for c in same[:n]]


def check(k=None):
    """What Settings shows after Check: does the key answer, and what one company costs."""
    if k:
        os.environ[ENV_KEY] = k
    j, err = _get("/companies/AAPL")
    if err:
        return {"ok": False, "error": err["message"]}
    name = ((j.get("company") or j).get("name") or "Apple").rstrip(".")
    return {"ok": True, "summary": (f"The key works: it answered for {name}. Opening a company's financials costs three calls, "
                                    "kept for twelve hours, plus one call a day for the company list, so the free plan's 250 calls a day covers about eighty companies. "
                                    "The Peers tab, when opened, spends one call per company in it, each kept a week.")}


def valid_key(k):
    return bool(re.fullmatch(r"sn_live_[A-Za-z0-9_-]{8,200}", (k or "").strip()))
