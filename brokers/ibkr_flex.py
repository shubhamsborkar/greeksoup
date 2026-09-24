"""Interactive Brokers (worldwide) through the Flex Web Service, which needs no
gateway program running: a token from Client Portal (Performance & Reports,
Flex Queries, Flex Web Service) and the id of a Flex Query the reader creates
with the Open Positions section (and, if they like, the Cash Report section).
Two calls: SendRequest returns a reference code, GetStatement returns the
report a few seconds later. The report is the previous close, so the desk
marks every line from Yahoo. Source: interactivebrokers.com, Flex Web Service
documentation, version 3."""

import time
import xml.etree.ElementTree as ET

import requests

from brokers import BrokerError, derive, last4, num

META = {
    "label": "Interactive Brokers",
    "where": "worldwide",
    "region": "us",
    "daily_login": False,
    "docs": "https://www.interactivebrokers.com/campus/ibkr-api-page/flex-web-service/",
    "prices": "Live prices: this connection reads your statements through Interactive Brokers' Flex service, which carries no live prices, so the desk prices your watchlist from the free feed. Interactive Brokers' Web API does serve live prices, through the Client Portal Gateway, a small program Interactive Brokers gives you to run on your computer. Your agent can add it from Interactive Brokers' Web API documentation, and the market data subscriptions on your Interactive Brokers login decide what it shows.",
    "how": "In Client Portal: Performance & Reports, Flex Queries. Create an Activity Flex Query with the Open Positions section (add Cash Report for the cash line), note its Query ID, then switch on Flex Web Service on the same page and copy the token. Positions are as of the previous close; the desk prices them live.",
    "fields": [
        {"env": "IBKR_FLEX_TOKEN", "label": "Flex Web Service token", "secret": True},
        {"env": "IBKR_FLEX_QUERY", "label": "Flex Query ID", "hint": "the number next to the query you created"},
    ],
}

SEND = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest"
GET = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/GetStatement"
UA = {"User-Agent": "GreekSoup desk (read-only Flex client)"}
REFRESH_S = 1800   # the report is end-of-day; ask for it at most twice an hour


def _fetch(cfg):
    try:
        r = requests.get(SEND, params={"t": cfg["IBKR_FLEX_TOKEN"], "q": cfg["IBKR_FLEX_QUERY"], "v": "3"},
                         headers=UA, timeout=30)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Interactive Brokers: " + str(exc)[:120]) from exc
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as exc:
        raise BrokerError("Interactive Brokers answered with something that is not a report.") from exc
    if (root.findtext("Status") or "") != "Success":
        msg = root.findtext("ErrorMessage") or "the request was refused"
        raise BrokerError("Interactive Brokers said: " + msg[:160] + ". Check the token and the Query ID in Client Portal.")
    ref = root.findtext("ReferenceCode")
    last = "the report was not ready"
    for _ in range(8):
        time.sleep(4)
        try:
            g = requests.get(GET, params={"t": cfg["IBKR_FLEX_TOKEN"], "q": ref, "v": "3"}, headers=UA, timeout=60)
        except requests.RequestException as exc:
            raise BrokerError("Could not reach Interactive Brokers: " + str(exc)[:120]) from exc
        text = g.text
        if "<FlexQueryResponse" in text or "<FlexStatements" in text:
            return ET.fromstring(text)
        try:
            err = ET.fromstring(text)
            last = err.findtext("ErrorMessage") or last
        except ET.ParseError:
            pass
    raise BrokerError("Interactive Brokers did not finish the report in time (" + last[:120] + "). Try again in a minute.")


def _parse(root):
    rows, cash, ccy, acct = [], None, "", ""
    for pos in root.iter("OpenPosition"):
        a = pos.attrib
        if str(a.get("assetCategory", "")).upper() not in ("STK", "ETF", "FUND", ""):
            continue
        acct = acct or a.get("accountId", "")
        qty = num(a.get("position"))
        sym = a.get("symbol") or ""
        rows.append(derive({
            "code": sym, "name": a.get("description") or "", "exch": a.get("listingExchange") or "",
            "qty": qty, "avg": num(a.get("costBasisPrice")),
            "ltp": None, "value": None, "pnl": None, "pnl_pct": None, "day_pct": None,
            "currency": a.get("currency") or "", "ysym": _ysym(sym, a.get("listingExchange") or ""),
            "close_mark": num(a.get("markPrice")),
        }))
    for c in root.iter("CashReportCurrency"):
        a = c.attrib
        if str(a.get("currency", "")).upper() == "BASE_SUMMARY":
            cash = num(a.get("endingCash"))
            ccy = ""
        elif cash is None:
            cash, ccy = num(a.get("endingCash")), a.get("currency") or ""
    for s in root.iter("FlexStatement"):
        acct = acct or s.attrib.get("accountId", "")
    return {"rows": rows, "cash": cash, "currency": ccy, "account": acct}


# A few listing exchanges and the suffix Yahoo uses for them. Unknown ones
# fall back to the bare symbol, which is right for US listings.
SUFFIX = {"LSE": ".L", "LSEETF": ".L", "IBIS": ".DE", "IBIS2": ".DE", "SBF": ".PA", "AEB": ".AS",
          "EBS": ".SW", "TSE": ".TO", "ASX": ".AX", "SEHK": ".HK", "TSEJ": ".T", "NSE": ".NS", "BSE": ".BO"}


def _ysym(sym, exch):
    return sym + SUFFIX.get(str(exch).upper(), "")


def connect(cfg, token=None):
    rep = _parse(_fetch(cfg))
    return {"cfg": cfg, "report": rep, "at": time.time()}


def _fresh(client):
    if time.time() - client["at"] > REFRESH_S:
        client["report"], client["at"] = _parse(_fetch(client["cfg"])), time.time()
    return client["report"]


def label(client):
    return last4(client["report"].get("account"))


def equity(client):
    return [dict(r) for r in _fresh(client)["rows"]]


def funds(client):
    rep = _fresh(client)
    ccy = rep.get("currency") or (rep["rows"][0]["currency"] if rep["rows"] else "")
    return {"cash": rep.get("cash"), "currency": ccy, "buying_power": None}
