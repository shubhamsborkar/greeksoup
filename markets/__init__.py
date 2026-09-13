"""The market layer: one file per home market, all from the public record.

A broker file says which market its accounts trade in (META["region"]); the
matching file here supplies what that market's public record offers, and the
desk shows it on Desk · Home, Watch · Home, Risk, Macro and the home ticker
page. Nothing here needs a key or a broker: a market file reads exchanges,
statistics offices and Yahoo.

Every market module has:
  META
    id               "in", "us" ...  (the broker file's region)
    label            "India"          (plain words, shown to the reader)
    currency         "INR"            symbol "₹"        locale "en-IN"
    exchanges        ["NSE", "BSE"]   the first is the default
    session_label    "NSE"            what the market-open dot says
    benchmark        "^NSEI"          Yahoo symbol of the index Risk measures against
    benchmark_label  "NIFTY 50"
    econ_country     "IN"             the economic calendar's country code
    filings          "NSE integrated filings"   where the ticker page's results come from
    units            "₹ Cr"           the unit those filings report in

  is_open(now=None)         -> bool          the regular session, in local time
  ysym(symbol, exch=None)   -> "RELIANCE.NS" Yahoo's symbol for an exchange symbol
optional
  macro_series()            -> [(id, label, unit, group, fetch)]  extra Macro cards;
                               fetch() returns [(date, value)] ascending
  macro_cards()             -> [card, ...]  cards built by the file itself
  results_calendar(symbols) -> {"rows": [...], "skipped": n}  upcoming results
  fundamentals(symbol)      -> the ticker page's filings block, or None
"""

import importlib
import os

REGISTRY = ["in", "us"]


def load(region):
    region = (region or "").strip().lower()
    if region not in REGISTRY:
        return None
    return importlib.import_module(f"markets.{region}")


def active(broker_region=None):
    """The home market: the broker's, else HOME_MARKET in .env, else none."""
    m = load(broker_region)
    if m:
        return m
    return load(os.getenv("HOME_MARKET", ""))


def all_meta():
    out = []
    for rid in REGISTRY:
        out.append(dict(load(rid).META))
    return out
