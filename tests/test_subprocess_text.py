"""Output from a child program is read in a way that cannot crash on Windows. Without an
encoding, Windows reads a child's output in its own character set (CP-1252 on an English
PC), and a UTF-8 web page with a letter that set lacks kills the reader thread: the desk
prints a trace in its window and the commodity card stays empty. Every Trading Economics
page carries one, the "Русский" link in its language menu (issue #5)."""
import ast
import os
import subprocess
import sys
import threading

import commods
import fred

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# a page shaped like the real one: the price sentence near the top, the language menu
# about 240 KB in, where the reader's traces stopped
TE_PAGE = ("<html><body><p>Coal rose to 143.75 USD/T on September 25, 2026, up 0.17% from the "
           "previous day.</p>" + "<div>" + "x" * 240_000 + "</div>"
           '<a href="https://ru.tradingeconomics.com/commodity/coal">Русский</a></body></html>').encode("utf-8")
FRED_CSV = "observation_date,DCOILWTICO\n2026-09-24,64.1\n2026-09-25,65.3\n# Русский\n".encode("utf-8")


def _child_writing(body, tmp_path):
    """subprocess.run as Windows would run it: the command swapped for a child that writes
    `body`, and CP-1252 as the character set when the caller names none. The body goes
    through a file because a 240 KB command line is too long for Linux and Windows."""
    real = subprocess.run
    src = tmp_path / "body"
    src.write_bytes(body)

    def run(cmd, **kw):
        if (kw.get("text") or kw.get("universal_newlines")) and not kw.get("encoding"):
            kw["encoding"] = "cp1252"
        code = "import sys; sys.stdout.buffer.write(open(sys.argv[1], 'rb').read())"
        return real([sys.executable, "-c", code, str(src)], **kw)
    return run


def _thread_errors(monkeypatch):
    seen = []
    monkeypatch.setattr(threading, "excepthook", lambda args: seen.append(args.exc_value))
    return seen


def test_trading_economics_page_reads_on_windows(monkeypatch, tmp_path):
    seen = _thread_errors(monkeypatch)
    monkeypatch.setattr(commods.subprocess, "run", _child_writing(TE_PAGE, tmp_path))
    monkeypatch.setattr(commods, "_cget", lambda k, t: None)
    monkeypatch.setattr(commods, "_cget_any", lambda k: None)
    monkeypatch.setattr(commods, "_cput", lambda k, v: None)
    te = commods.te_current("coal")
    assert te and te["level"] == 143.75 and te["unit"] == "USD/T" and te["date"] == "2026-09-25"
    assert te["d1"] == 0.17
    assert not seen


def test_fred_reads_on_windows(monkeypatch, tmp_path):
    seen = _thread_errors(monkeypatch)
    monkeypatch.setattr(fred.subprocess, "run", _child_writing(FRED_CSV, tmp_path))
    assert fred.csv("DCOILWTICO")[:2] == [("2026-09-24", 64.1), ("2026-09-25", 65.3)]
    assert not seen


def _shipped_files():
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("tests", "scripts", "cache", "data", "logs")]
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def test_every_text_read_of_a_child_says_what_to_do_with_a_bad_byte():
    """A new call that reads a child as text must set errors=, so it can never crash on a
    character the reader's PC lacks."""
    missing = []
    for path in _shipped_files():
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("run", "Popen", "check_output")
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"):
                continue
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            text = any(isinstance(kw.get(k), ast.Constant) and kw[k].value for k in ("text", "universal_newlines"))
            if (text or "encoding" in kw) and "errors" not in kw:
                missing.append(f"{os.path.relpath(path, HERE)}:{node.lineno}")
    assert not missing, "set errors= (and encoding= for web pages) on: " + ", ".join(missing)
