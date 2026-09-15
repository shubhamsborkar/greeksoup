"""An update never loses saved work.

Every file the reader owns carries a `format` number. When a release changes a file's shape it
bumps the owner's FORMAT and registers a migration (old format -> next); at the next start the
desk keeps a copy of every such file under cache/previous/migrate-<version>/, brings the file
up to the new shape, and says so on the update banner with where the copy is. A file written
by a NEWER desk (a vault synced from another computer) is left alone and named on the banner.

The registry below is the list of what the reader owns. A kind names its files, its current
format and its migrations; `tests/` fails the release if a FORMAT rose with no migration for
the step below it, and scripts/make_manifest.py prints every owner and shipped starter a
release touches so the author sees the warning before it ships.
"""
import glob
import json
import os
import shutil
import time
from datetime import datetime

import notes as desk_notes
import chains as desk_chains

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
PREVIOUS = os.path.join(HERE, "cache", "previous")
REPORT_PATH = os.path.join(HERE, "cache", "migrations.json")
REPORT_SHOWN_FOR = 7 * 24 * 3600


def _data(*names):
    return lambda: [p for p in (os.path.join(DATA_DIR, n) for n in names) if os.path.isfile(p)]


def _vault(pattern):
    return lambda: sorted(glob.glob(os.path.join(desk_notes.RESEARCH_DIR, pattern)))


# ---- what the reader owns -------------------------------------------------------------------
# kind: a name; label: words for the banner; paths: the files now; format: the shape this desk
# writes; migrations: {from_format: fn(dict) -> dict} one step each; owner: the module that
# writes the kind (the release gate watches it). Format 0 means "from before formats": the
# step 0 -> 1 only stamps the number unless a migration is registered.
KINDS = [
    {"kind": "chain", "label": "your chains", "paths": _vault("chains/*.json"),
     "format": lambda: desk_chains.FORMAT, "migrations": lambda: desk_chains.MIGRATIONS, "owner": "chains.py"},
    {"kind": "book", "label": "Desk · Book", "paths": _data("book.json"),
     "format": lambda: 1, "migrations": lambda: {}, "owner": "server.py"},
    {"kind": "us_book", "label": "the hand-kept US book", "paths": _data("us_book.json"),
     "format": lambda: 1, "migrations": lambda: {}, "owner": "server.py"},
    {"kind": "watch", "label": "your watchlists", "paths": _data("watchlist.json", "watchlist_us.json", "watchlist_global.json"),
     "format": lambda: 1, "migrations": lambda: {}, "owner": "server.py"},
    {"kind": "alerts", "label": "your alert rules", "paths": _data("alerts.json"),
     "format": lambda: 1, "migrations": lambda: {}, "owner": "server.py"},
]

# shipped starters: files beside the code the desk reads as examples; the updater refreshes
# them only while the reader has not edited them, so a change here is a change readers see
STARTERS = ["data/supply_chain.json", "data/commodities.json", "data/exposure_us.json",
            "data/exposure_example.json", "data/funds.json", "data/members.json", "data/alerts.json"]


def owners():
    return sorted({k["owner"] for k in KINDS} | {"notes.py", "migrate.py"})


def check_registry(kinds=None):
    """Every step below the current format has a migration (0 -> 1 excepted). Returns the
    problems as words; empty when the registry is sound."""
    out = []
    for k in kinds or KINDS:
        fmt, mig = k["format"](), k["migrations"]()
        for step in range(1, fmt):
            if step not in mig:
                out.append(f"{k['kind']}: format {fmt} but no migration from {step} to {step + 1}")
    return out


# ---- the run at start ------------------------------------------------------------------------
def _read(path):
    """The file as a dict, and the indent it was written with, so a rewrite keeps its look."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        d = json.loads(text)
        indent = len(text.split("\n", 1)[1]) - len(text.split("\n", 1)[1].lstrip(" ")) if "\n" in text else 2
        return (d, indent or 2) if isinstance(d, dict) else (None, 2)
    except (OSError, ValueError, IndexError):
        return (None, 2)


def _keep(path, version):
    """A copy of the file as it was, under cache/previous/migrate-<version>/, by its path."""
    rel = os.path.relpath(path, HERE) if path.startswith(HERE) else os.path.basename(path)
    dst = os.path.join(PREVIOUS, f"migrate-{version}", rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(path, dst)
    return dst


def run(version="", kinds=None, write_report=True):
    """Bring every reader-owned file up to this desk's shape. Returns the report; nothing is
    touched when every file is already current."""
    rep = {"at": time.time(), "when": datetime.now().strftime("%Y-%m-%d %H:%M"), "version": version,
           "migrated": [], "newer": [], "errors": []}
    for k in kinds or KINDS:
        try:
            cur, mig = k["format"](), k["migrations"]()
            paths = k["paths"]()
        except Exception as exc:  # noqa: BLE001
            rep["errors"].append(f"{k['kind']}: {exc}")
            continue
        for path in paths:
            d, indent = _read(path)
            if d is None:
                continue
            try:
                have = int(d.get("format", 0) or 0)
            except (TypeError, ValueError):
                have = 0
            if have == cur:
                continue
            if have > cur:
                rep["newer"].append({"kind": k["kind"], "label": k["label"], "path": path, "format": have, "desk": cur})
                continue
            try:
                kept = _keep(path, version or "unversioned")
                for step in range(have, cur):
                    fn = mig.get(step)
                    if fn:
                        d = fn(d)
                d["format"] = cur
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(d, fh, indent=indent, ensure_ascii=False)
                    fh.write("\n")
                os.replace(tmp, path)
                rep["migrated"].append({"kind": k["kind"], "label": k["label"], "path": path,
                                        "from": have, "to": cur, "kept": kept,
                                        "stamped": not any(step in mig for step in range(have, cur))})   # only the number changed
            except Exception as exc:  # noqa: BLE001
                rep["errors"].append(f"{path}: {exc}")
    real = [m for m in rep["migrated"] if not m["stamped"]]
    if write_report and (real or rep["newer"] or rep["errors"]):
        try:
            os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
            with open(REPORT_PATH, "w", encoding="utf-8") as fh:
                json.dump({**rep, "migrated": real}, fh, indent=1)
        except OSError:
            pass
    return rep


def last_report():
    """What the banner shows: the last run that changed a file's shape, for a week."""
    try:
        with open(REPORT_PATH, encoding="utf-8") as fh:
            r = json.load(fh)
        if time.time() - r.get("at", 0) < REPORT_SHOWN_FOR and (r.get("migrated") or r.get("newer") or r.get("errors")):
            return r
    except (OSError, ValueError):
        pass
    return None
