"""The desk records its own errors and the check reads them back. Issue #5's reader ran
the desk from Start Desk, so 26 traces a refresh went to the window and nowhere else, and
the check said "Nothing to fix"."""
import os
import shutil
import subprocess
import sys
import threading
import time

import pytest

import errlog

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def log(monkeypatch, tmp_path):
    monkeypatch.setattr(errlog, "PATH", str(tmp_path / "logs" / "desk-errors.log"))
    monkeypatch.setattr(threading, "excepthook", threading.excepthook)   # restored after the test
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    errlog.install()
    return tmp_path


def _boom():
    raise UnicodeDecodeError("charmap", b"\x81", 0, 1, "character maps to <undefined>")


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")   # the error still reaches the old printer
def test_an_error_in_a_background_thread_is_recorded(log):
    t = threading.Thread(target=_boom, name="Thread-12 (_readerthread)")
    t.start()
    t.join()
    got = errlog.recent()
    assert len(got) == 1 and got[0]["where"] == "in Thread-12 (_readerthread)"
    assert got[0]["last"].startswith("UnicodeDecodeError: 'charmap' codec can't decode byte 0x81")
    assert "Traceback" in got[0]["text"]


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")   # the error still reaches the old printer
@pytest.mark.skipif(os.name != "nt", reason="only Windows reads a child's output in a reader thread")
def test_the_issue_5_reader_thread_failure_is_recorded_on_windows(log):
    body = "Русский".encode("utf-8")
    try:
        subprocess.run([sys.executable, "-c", f"import sys; sys.stdout.buffer.write({body!r})"],
                       capture_output=True, encoding="cp1252", timeout=30)
    except Exception:  # noqa: BLE001 - the caller's own error is not what this test is about
        pass
    got = errlog.recent()
    assert got and "_readerthread" in got[0]["where"] and "0x81" in got[0]["last"]


def test_only_the_last_day_counts_and_the_file_rolls_over(log, monkeypatch):
    for _ in range(3):
        try:
            _boom()
        except UnicodeDecodeError:
            errlog.write("in a test", *sys.exc_info())
    assert len(errlog.recent()) == 3
    assert errlog.recent(now=time.time() + 25 * 3600) == []
    monkeypatch.setattr(errlog, "MAX_BYTES", 10)
    try:
        _boom()
    except UnicodeDecodeError:
        errlog.write("in a test", *sys.exc_info())
    assert os.path.isfile(errlog.PATH + ".1") and len(errlog.recent()) == 4


def test_the_check_shows_the_errors_and_stops_saying_nothing_to_fix(tmp_path):
    for f in ("doctor.py", "errlog.py"):
        shutil.copy(os.path.join(HERE, f), tmp_path / f)
    (tmp_path / "server.py").write_text("")          # the check looks for the desk's own files
    os.makedirs(tmp_path / "logs")
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    trace = ("Traceback (most recent call last):\n  File \"subprocess.py\", line 1615, in _readerthread\n"
             "UnicodeDecodeError: 'charmap' codec can't decode byte 0x81 in position 242313: character maps to <undefined>\n")
    with open(tmp_path / "logs" / "desk-errors.log", "w", encoding="utf-8") as fh:
        for n, pos in ((12, 242313), (14, 242952), (16, 234578)):
            fh.write(f"=== {stamp} | in Thread-{n} (_readerthread)\n{trace.replace('242313', str(pos))}")
    out = subprocess.run([sys.executable, str(tmp_path / "doctor.py"), "--offline"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=60,
                         env={**os.environ, "PYTHONIOENCODING": "utf-8"}).stdout
    assert "the desk hit 3 error(s) in the last day, 1 kind(s)" in out
    assert "3 x UnicodeDecodeError: 'charmap' codec can't decode byte 0x81 in position …" in out
    assert "ours to fix" in out and "Nothing to fix" not in out
