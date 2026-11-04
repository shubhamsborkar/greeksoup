"""The Dividends tab reads the free feed's payment record: newest first, ex-dates in the
exchange's own day, share classes asked for with a dash, and nothing raised when the feed rests."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import freefeed  # noqa: E402


class _R:
    def __init__(self, j):
        self._j = j

    def json(self):
        return self._j


def test_payments_newest_first_and_dash_symbol(monkeypatch):
    asked = {}

    def fake(path, params):
        asked["path"], asked["params"] = path, params
        return _R({"chart": {"result": [{"meta": {"gmtoffset": -18000},
                                         "events": {"dividends": {"1": {"amount": 0.26, "date": 1770647400},
                                                                  "2": {"amount": 0.27, "date": 1778506200}}}}]}})
    monkeypatch.setattr(freefeed, "_get", fake)
    rows = freefeed.dividends("BRK.B")
    assert asked["path"].endswith("/BRK-B") and asked["params"]["events"] == "div"
    assert [r["dividend"] for r in rows] == [0.27, 0.26]
    assert rows[0]["date"] == "2026-05-11"


def test_resting_feed_is_empty(monkeypatch):
    monkeypatch.setattr(freefeed, "_get", lambda path, params: None)
    assert freefeed.dividends("AAPL") == []
