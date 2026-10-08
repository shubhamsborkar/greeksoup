"""A ticker Yahoo does not know must fail on its own and never pause the feed for every other
name; only Yahoo saying too many requests does that. No network: requests.get is replaced."""
import time

import freefeed


class _R:
    def __init__(self, code):
        self.status_code = code


def _run(monkeypatch, codes):
    seq = iter(codes)
    monkeypatch.setattr(freefeed.requests, "get", lambda *a, **k: _R(next(seq, codes[-1])))
    monkeypatch.setitem(freefeed._throttle, "until", 0.0)
    return freefeed._get("/v8/finance/chart/X", {})


def test_unknown_symbol_does_not_pause_the_feed(monkeypatch):
    assert _run(monkeypatch, [404]) is None
    assert not freefeed.resting()


def test_too_many_requests_pauses_five_minutes(monkeypatch):
    assert _run(monkeypatch, [429]) is None
    assert freefeed.resting()
    assert freefeed._throttle["until"] - time.time() > 240


def test_no_answer_at_all_pauses_one_minute(monkeypatch):
    def boom(*a, **k):
        raise OSError("offline")
    monkeypatch.setattr(freefeed.requests, "get", boom)
    monkeypatch.setitem(freefeed._throttle, "until", 0.0)
    assert freefeed._get("/x", {}) is None
    assert 0 < freefeed._throttle["until"] - time.time() <= 61


def test_success_after_a_429_is_returned(monkeypatch):
    r = _run(monkeypatch, [429, 200])
    assert r is not None and r.status_code == 200
    assert not freefeed.resting()


def test_why_empty_tells_unknown_from_paused(monkeypatch):
    _run(monkeypatch, [404])
    assert freefeed.why_empty() == "unknown"
    _run(monkeypatch, [429])
    assert freefeed.why_empty() == "paused"
    # while paused, nothing is asked and the reason stays "paused"
    assert freefeed._get("/x", {}) is None
    assert freefeed.why_empty() == "paused"


def test_exchange_answering_with_nothing_is_not_a_failure(monkeypatch):
    import nse_fund

    def answered(*a, **k):
        nse_fund._answered["ok"] = True
        return []
    for f in ("quarterly_results", "shareholding", "announcements"):
        monkeypatch.setattr(nse_fund, f, answered)
    r = nse_fund.build("ZZQXJ")
    assert r["none_listed"] and r["quarters"] == []

    def silent(*a, **k):
        return []
    for f in ("quarterly_results", "shareholding", "announcements"):
        monkeypatch.setattr(nse_fund, f, silent)
    assert nse_fund.build("ZZQXJ") is None


def test_insiders_name_a_refused_source(monkeypatch):
    import sec_form4
    monkeypatch.setattr(sec_form4, "cik_map", lambda: {"AAPL": ("0000320193", "Apple"), "MSFT": ("0000789019", "Microsoft")})
    monkeypatch.setattr(sec_form4, "_get", lambda *a, **k: None)
    monkeypatch.setattr(sec_form4, "_tx_cache", {})
    out = sec_form4.build(["AAPL", "MSFT"])
    assert out["refused"] == ["AAPL", "MSFT"] and out["all_refused"] and out["_ttl"] == 600
