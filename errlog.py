"""The desk's own record of its errors, whichever way it was started.

A desk started from Start Desk prints to its window and nowhere else, so an error in a
background thread (issue #5: a Commodities read failing on Windows, 26 traces every ten
minutes) never reached a file, and the check said "Nothing to fix". `install()` keeps
printing every error where it always printed and also appends it, dated, to
logs/desk-errors.log; `recent()` is what the check reads back.
"""
import os
import sys
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "logs", "desk-errors.log")
MAX_BYTES = 512 * 1024          # past this the file moves to desk-errors.log.1, one old copy kept
HEAD = "=== "                   # every entry starts "=== 2026-09-28 18:00:00 | where"
_lock = threading.Lock()


def write(where, exc_type, exc, tb):
    """Append one error. Never raises: a broken log must not add a second error."""
    try:
        text = "".join(traceback.format_exception(exc_type, exc, tb)).rstrip()
        entry = f"{HEAD}{time.strftime('%Y-%m-%d %H:%M:%S')} | {where}\n{text}\n"
        with _lock:
            os.makedirs(os.path.dirname(PATH), exist_ok=True)
            if os.path.isfile(PATH) and os.path.getsize(PATH) > MAX_BYTES:
                os.replace(PATH, PATH + ".1")
            with open(PATH, "a", encoding="utf-8", errors="replace") as fh:
                fh.write(entry)
    except Exception:  # noqa: BLE001
        pass


def install():
    """Record uncaught errors in the main thread and in every other thread, and still
    print them exactly as before."""
    before_thread, before_main = threading.excepthook, sys.excepthook

    def on_thread(args):
        if args.exc_type is not SystemExit:
            name = args.thread.name if args.thread else "a thread"
            write(f"in {name}", args.exc_type, args.exc_value, args.exc_traceback)
        before_thread(args)

    def on_main(exc_type, exc, tb):
        if exc_type is not KeyboardInterrupt:
            write("at the top of the desk", exc_type, exc, tb)
        before_main(exc_type, exc, tb)

    threading.excepthook, sys.excepthook = on_thread, on_main


def recent(hours=24, now=None):
    """Entries from the last `hours`, oldest first: [{"at", "where", "text", "last"}],
    `last` being the error's own final line ("UnicodeDecodeError: ...")."""
    now = now if now is not None else time.time()
    out = []
    for path in (PATH + ".1", PATH):
        try:
            raw = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for chunk in raw.split("\n" + HEAD) if raw.startswith(HEAD) else []:
            chunk = chunk[len(HEAD):] if chunk.startswith(HEAD) else chunk
            head, _, body = chunk.partition("\n")
            at, _, where = head.partition(" | ")
            try:
                t = time.mktime(time.strptime(at.strip(), "%Y-%m-%d %H:%M:%S"))
            except ValueError:
                continue
            if now - t <= hours * 3600:
                body = body.rstrip()
                out.append({"at": at.strip(), "where": where.strip(), "text": body,
                            "last": (body.splitlines() or [""])[-1]})
    return out
