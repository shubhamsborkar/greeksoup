"""The Commodities board reads a Trading Economics card from the page's summary sentence.
A quiet day reads "traded flat at", which the board missed, so cobalt, synthetic rubber
and kraft pulp, which trade flat most days, had no current price anywhere."""
import subprocess

import commods

MOVED = ("<p>Coal rose to 143.75 USD/T on September 25, 2026, up 0.17% from the previous day. "
         "Over the past month, Coal's price has risen 3.2%, and is up 12.5% compared to the same "
         "time last year, according to trading on a contract for difference (CFD).</p>")
FLAT = ("<p>Cobalt traded flat at 39,640 USD/T on September 24, 2026. Over the past month, "
        "Cobalt&#39;s price has fallen 29.58%, but it is still 14.73% higher than a year ago, "
        "according to trading on a contract for difference (CFD).</p>")
ELSEWHERE = "<div>" + "x" * 2000 + "</div><p>Lithium fell 1.5% from the previous day.</p>"


def _page(monkeypatch, body):
    monkeypatch.setattr(commods, "_cget", lambda k, t: None)
    monkeypatch.setattr(commods, "_cget_any", lambda k: None)
    monkeypatch.setattr(commods, "_cput", lambda k, v: None)
    monkeypatch.setattr(commods.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=body, stderr=""))


def test_a_move_reads_level_and_every_window(monkeypatch):
    _page(monkeypatch, MOVED)
    te = commods.te_current("coal")
    assert (te["level"], te["unit"], te["date"]) == (143.75, "USD/T", "2026-09-25")
    assert (te["d1"], te["m1"], te["y1"]) == (0.17, 3.2, 12.5)


def test_a_flat_day_reads_and_its_day_move_is_zero(monkeypatch):
    _page(monkeypatch, FLAT)
    te = commods.te_current("cobalt")
    assert (te["level"], te["unit"], te["date"]) == (39640.0, "USD/T", "2026-09-24")
    assert (te["d1"], te["m1"], te["y1"]) == (0.0, -29.58, 14.73)


def test_a_move_elsewhere_on_the_page_is_not_this_cards(monkeypatch):
    _page(monkeypatch, FLAT + ELSEWHERE.replace("fell 1.5% from", "down 1.5% from"))
    assert commods.te_current("cobalt")["d1"] == 0.0
