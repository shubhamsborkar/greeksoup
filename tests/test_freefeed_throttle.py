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
