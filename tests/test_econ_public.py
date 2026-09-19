"""The public-record economic calendar: the Eastern-to-UTC rule and the two page parsers,
offline, on the shapes the pages had on 2026-09-19."""
import re
from datetime import date

import econ_public as e


def test_eastern_offset_rule():
    assert e._et_offset_hours(date(2026, 1, 15)) == -5       # standard time
    assert e._et_offset_hours(date(2026, 3, 8)) == -4        # second Sunday of March 2026, daylight begins
    assert e._et_offset_hours(date(2026, 3, 7)) == -5
    assert e._et_offset_hours(date(2026, 7, 4)) == -4
    assert e._et_offset_hours(date(2026, 11, 1)) == -5       # first Sunday of November 2026, standard resumes
    assert e._et_offset_hours(date(2026, 10, 31)) == -4
    assert e._et_to_utc(date(2026, 10, 14), 8, 30) == ("2026-10-14", "12:30")
    assert e._et_to_utc(date(2026, 12, 9), 14, 0) == ("2026-12-09", "19:00")


def test_bls_cell_parser_shape():
    cell = '<p class="day">14</p><p><strong>Consumer Price Index<br></strong>September 2026<br>08:30 AM</p><p><strong>Real Earnings<br></strong>September 2026<br>08:30 AM</p>'
    found = re.findall(r"<strong>(.*?)<br></strong>(.*?)<br>(\d{1,2}:\d{2} [AP]M)</p>", cell, flags=re.S)
    assert found == [("Consumer Price Index", "September 2026", "08:30 AM"), ("Real Earnings", "September 2026", "08:30 AM")]
    assert any(k in "consumer price index" for k in e.BLS_HIGH)


def test_forex_factory_row_shape(monkeypatch):
    class R:
        status_code = 200
        def json(self):
            return [{"title": "CPI m/m", "country": "USD", "date": "2026-10-14T08:30:00-04:00", "impact": "High", "forecast": "0.3%", "previous": "0.2%"},
                    {"title": "Bank Holiday", "country": "All", "date": "2026-10-12T00:00:00-04:00", "impact": "Holiday", "forecast": "", "previous": ""}]
    monkeypatch.setattr(e.requests, "get", lambda *a, **k: R())
    rows = e.forex_factory()
    assert rows == [{"date": "2026-10-14", "time": "12:30", "country": "US", "event": "CPI m/m", "impact": "High",
                     "estimate": "0.3%", "previous": "0.2%", "actual": None, "period": "", "unit": ""}]
