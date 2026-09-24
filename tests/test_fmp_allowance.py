"""FMP's free plan allows 250 market data requests a day (FMP's FAQ). The US price sweep
must not spend a free key in minutes; a key that has shown it is paid sweeps as before."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import server  # noqa: E402


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    monkeypatch.setattr(server, "FMP_PLAN_PATH", str(tmp_path / "fmp_plan.json"))
    server._fmp_day.update(date="", calls=0, ok=0)


def test_a_new_key_spreads_the_sweep_across_the_session(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    gap = server.fmp_sweep_gap(10, True)
    sweeps = server.US_SESSION_SECONDS / gap
    assert sweeps * 10 <= server.FMP_SWEEP_SHARE < server.FMP_FREE_DAILY


def test_a_key_that_answers_past_the_free_allowance_is_paid(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    for _ in range(server.FMP_FREE_DAILY):
        server._fmp_count(True)
    assert not server.fmp_paid()
    server._fmp_count(True)
    assert server.fmp_paid()
    assert server.fmp_sweep_gap(10, True) == 0


def test_refused_calls_do_not_make_a_key_paid(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    for _ in range(server.FMP_FREE_DAILY + 50):
        server._fmp_count(False)
    assert not server.fmp_paid()
