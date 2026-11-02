"""Shikshan Nivesh Data fills the statements and segments in the shape the ticker page reads:
newest first, quarters named by the company's own fiscal year, cash going out negative, and a
refusal (no key, day's calls used, company not covered) said in words, never raised."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from data_providers import shikshan_nivesh as sn  # noqa: E402

# a company whose year ends in February (BlackBerry's shape), cut to two years and three quarters
FIN = {
    "currency": "USD", "access": {"record": "full"},
    "annual": {
        "IS": {"periods": ["2025-02-28", "2026-02-28"],
               "lines": [{"id": "rev", "sign": None, "values": {"2025-02-28": 534.9e6, "2026-02-28": 620.0e6}},
                         {"id": "eps_dil", "sign": None, "values": {"2026-02-28": 0.05}}]},
        "BS": {"periods": ["2026-02-28"], "lines": [{"id": "ar", "sign": "+", "values": {"2026-02-28": 90e6}}]},
        "CF": {"periods": ["2026-02-28"],
               "lines": [{"id": "capex", "sign": "-", "values": {"2026-02-28": 5e6}},
                         {"id": "cfo", "sign": None, "values": {"2026-02-28": 40e6}}]},
    },
    "quarterly": {
        "IS": {"periods": ["2026-02-28", "2026-05-31", "2026-08-31"],
               "lines": [{"id": "rev", "sign": None, "values": {"2026-02-28": 156e6, "2026-05-31": 152.9e6, "2026-08-31": 163.3e6}}]},
    },
}
SEG = {"segments": {"product": {"years": ["2025-02-28", "2026-02-28"],
                                "rows": [{"label": "Cybersecurity", "values": {"2025-02-28": 270e6, "2026-02-28": 280e6}},
                                         {"label": "IoT", "values": {"2025-02-28": None, "2026-02-28": 250e6}}]}}}


def _answer(monkeypatch, fin=FIN, seg=SEG, err=None):
    def fake(path, **params):
        if err:
            return None, err
        return (fin if path.endswith("/financials") else seg), None
    monkeypatch.setattr(sn, "_get", fake)


def test_rows_are_newest_first_in_the_company_fiscal_year(monkeypatch):
    _answer(monkeypatch)
    s = sn.statements("BB")
    assert [r["date"] for r in s["inc_a"]] == ["2026-02-28", "2025-02-28"]
    assert s["inc_a"][0]["fiscalYear"] == "2026" and s["inc_a"][0]["period"] == "FY"
    assert [(r["period"], r["fiscalYear"]) for r in s["inc_q"]] == [("Q2", "2027"), ("Q1", "2027"), ("Q4", "2026")]
    assert s["inc_a"][0]["revenue"] == 620.0e6 and s["inc_a"][0]["epsDiluted"] == 0.05


def test_cash_going_out_is_negative_and_receivables_fall_back(monkeypatch):
    _answer(monkeypatch)
    s = sn.statements("BB")
    assert s["cf_a"][0]["capitalExpenditure"] == -5e6
    assert s["cf_a"][0]["operatingCashFlow"] == 40e6
    assert s["bs_a"][0]["netReceivables"] == 90e6


def test_segments_take_the_page_shape(monkeypatch):
    _answer(monkeypatch)
    g = sn.segments("BB")
    assert g["seg_p"][-1] == {"date": "2026-02-28", "fiscalYear": 2026, "period": "FY",
                              "data": {"Cybersecurity": 280e6, "IoT": 250e6}}
    assert g["seg_p"][0]["data"] == {"Cybersecurity": 270e6}
    assert g["seg_g"] == []


def test_a_refusal_is_said_never_raised(monkeypatch):
    _answer(monkeypatch, err={"kind": "limit", "message": "This account has used its 250 free calls for today."})
    assert sn.statements("BB")["error"]["kind"] == "limit"
    assert sn.segments("BB") == {}


def test_no_key_asks_nothing(monkeypatch):
    monkeypatch.delenv(sn.ENV_KEY, raising=False)
    j, err = sn._get("/companies/AAPL")
    assert j is None and err["kind"] == "no_key"


FIG = {"periods": {"annual": [{"end": "2025-02-28", "label": "FY2025"}, {"end": "2026-02-28", "label": "FY2026"}]},
       "figures": [{"id": "net_margin", "annual": {"2025-02-28": -14.8, "2026-02-28": 9.69}},
                   {"id": "current_ratio", "annual": {"2026-02-28": 2.12}},
                   {"id": "roe", "annual": {"2026-02-28": 7.26}}]}


def test_ratios_take_the_tab_shape(monkeypatch):
    monkeypatch.setattr(sn, "_get", lambda path, **p: (FIG, None))
    r = sn.ratios("BB")
    assert [x["fiscalYear"] for x in r["ratios"]] == ["2026", "2025"]
    assert abs(r["ratios"][0]["netProfitMargin"] - 0.0969) < 1e-9 and r["ratios"][0]["currentRatio"] == 2.12
    assert abs(r["metrics"][0]["returnOnEquity"] - 0.0726) < 1e-9
