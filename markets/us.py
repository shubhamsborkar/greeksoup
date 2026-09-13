"""The United States as a home market. Its earnings countdown, insider tape and
pulse already live on Desk · US, so this file only carries what the home
screens need to follow a US broker: the session, the index and the currency."""

from datetime import datetime, timezone

META = {
    "id": "us",
    "label": "United States",
    "currency": "USD", "symbol": "$", "locale": "en-US",
    "exchanges": ["NASDAQ", "NYSE"],
    "session_label": "US",
    "benchmark": "^GSPC", "benchmark_label": "S&P 500",
    "econ_country": "US",
    "filings": "", "units": "",
}


def is_open(now=None):
    """The regular session, 13:30 to 20:00 UTC (covers daylight time; close
    enough for a status dot, the data itself is whatever the feed serves)."""
    now = now or datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return False
    hm = now.hour * 60 + now.minute
    return (13 * 60 + 30) <= hm < (20 * 60)


def ysym(symbol, exch=None):
    return (symbol or "").upper()
