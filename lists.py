"""The reader's own lists: one pattern for every list a screen runs on.

A shipped list is a starter, never the reader's own. Each kind below names its fields, its key
and where the starter rows come from. The reader's rows live in the research vault
(data/research/lists/<kind>.json, format 1), so they sync, back up and restore with the notes.
The list a screen sees is the starters the reader has not put away, each replaced in place by
the reader's edited copy where one exists, followed by the rows the reader added. Remove keeps
a copy so Undo can bring it back; a starter put away comes back with "Bring the starters back".
"""
import json
import os
import re
import threading
from datetime import datetime

import notes as desk_notes

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
FORMAT = 1
MIGRATIONS = {}
_lock = threading.Lock()


def _json(name, key):
    def read():
        try:
            with open(os.path.join(DATA_DIR, name), encoding="utf-8") as fh:
                rows = json.load(fh).get(key, [])
            return [r for r in rows if isinstance(r, dict)]
        except (OSError, ValueError):
            return []
    return read


MACRO_STARTERS = []     # the server hands its MACRO_SERIES table in at import: (fred id, label, unit, group)


def _macro_starters():
    return [{"id": r[0], "label": r[1], "unit": r[2], "group": r[3]} for r in MACRO_STARTERS]


# field: (key, label, kind, required) ; kind: text | list | select:a|b ; the first field is the
# one a row is named by on the screen, `key` is the field that makes a row unique
KINDS = {
    "funds": {
        "label": "Funds you follow", "one": "fund", "key": "cik", "starter": _json("funds.json", "funds"),
        "screen": "/funds", "caches": ["funds", "act13d"],
        "fields": [("name", "Fund", "text", True), ("cik", "CIK", "text", True), ("note", "Note", "text", False)],
        "hint": "A fund is followed by its CIK, the number on its 13F filings; EDGAR's company search gives it from the name.",
    },
    "members": {
        "label": "Members you track", "one": "member", "key": "name", "starter": _json("members.json", "members"),
        "screen": "/capitol", "caches": ["capitol"],
        "fields": [("label", "Full name", "text", True), ("name", "Surname on the filings", "text", True),
                   ("chamber", "Chamber", "select:house|senate", True)],
        "hint": "The surname is how the disclosure feed files them; the full name is what the screen shows.",
    },
    "macro": {
        "label": "Macro series", "one": "series", "key": "id", "starter": _macro_starters,
        "screen": "/macro", "caches": ["macro"],
        "fields": [("label", "Label", "text", True), ("id", "FRED series", "text", True), ("unit", "Unit", "text", False),
                   ("group", "Group", "text", True)],
        "hint": "Any series FRED publishes, by its id (DGS10, CPIAUCSL). Unit %yoy shows the year-on-year change of a level; k shows thousands. Groups become the page's sections.",
    },
    "commodities": {
        "label": "Commodities on the board", "one": "commodity", "key": "id", "starter": _json("commodities.json", "commodities"),
        "screen": "/commods", "caches": ["commods"],
        "fields": [("label", "Commodity", "text", True), ("id", "Short id", "text", True), ("group", "Group", "text", True),
                   ("unit", "Unit", "text", False), ("yahoo", "Yahoo symbol", "text", False), ("fred", "FRED series", "text", False),
                   ("cost", "Who pays it (cost)", "list", False), ("revenue", "Who earns it (revenue)", "list", False),
                   ("note", "Note", "text", False)],
        "hint": "A Yahoo symbol (CL=F, HG=F, ZW=F) gives a daily series; a FRED series stands in when Yahoo has none. Cost and revenue are the industries a move lands on, one per line.",
        "flatten": {"yahoo": ("sources", "yahoo"), "fred": ("sources", "fred")},
    },
    "fno": {
        "label": "Names on the options tape", "one": "name", "key": "stock_code", "starter": _json("fno_watchlist.json", "names"),
        "screen": "/", "caches": ["tape"],
        "fields": [("stock_code", "Code", "text", True), ("exchange_code", "Exchange", "text", True)],
        "hint": "The index or stock codes your broker serves option chains for, in the broker's own spelling.",
    },
}


# ---- storage ----------------------------------------------------------------------------------
def lists_dir():
    return os.path.join(desk_notes.RESEARCH_DIR, "lists")


def _path(kind):
    return os.path.join(lists_dir(), kind + ".json")


def _previous_dir():
    return os.path.join(lists_dir(), ".previous")


def _read(kind):
    try:
        with open(_path(kind), encoding="utf-8") as fh:
            d = json.load(fh)
        if not isinstance(d, dict):
            raise ValueError
    except (OSError, ValueError):
        d = {}
    return {"format": FORMAT, "rows": [r for r in d.get("rows", []) if isinstance(r, dict)],
            "hidden": [str(x) for x in d.get("hidden", [])]}


def _write(kind, d):
    os.makedirs(lists_dir(), exist_ok=True)
    d["format"] = FORMAT
    d["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    tmp = _path(kind) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, _path(kind))


# ---- rows ------------------------------------------------------------------------------------
def _flat(kind, row):
    """A starter row in the form's shape (nested sources lifted to fields)."""
    spec = KINDS[kind]
    out = dict(row)
    for fkey, path in spec.get("flatten", {}).items():
        v = row
        for p in path:
            v = v.get(p, {}) if isinstance(v, dict) else {}
        out[fkey] = v if isinstance(v, str) else ""
    return out


def _nest(kind, row):
    """The reverse: the form's shape back to what the screen's builder reads."""
    spec = KINDS[kind]
    out = dict(row)
    for fkey, path in spec.get("flatten", {}).items():
        v = out.pop(fkey, "")
        nested = dict(out.get(path[0]) or {})
        if v:
            nested[path[1]] = v
        else:
            nested.pop(path[1], None)
        out[path[0]] = nested
    return out


def _clean(kind, row):
    """One row in the desk's shape; raises ValueError with words for the reader."""
    spec = KINDS[kind]
    out = {}
    for key, label, ftype, required in spec["fields"]:
        v = row.get(key, "")
        if ftype == "list":
            if isinstance(v, str):
                v = v.splitlines()
            v = [str(x).strip()[:120] for x in (v or []) if str(x).strip()][:40]
        elif ftype.startswith("select:"):
            allowed = ftype.split(":", 1)[1].split("|")
            v = str(v or "").strip().lower()
            if v and v not in allowed:
                raise ValueError(f"{label} must be one of {', '.join(allowed)}.")
        else:
            v = str(v if v is not None else "").strip()[:400]
            if key == spec["key"]:
                v = re.sub(r"\s+", " ", v)
        if required and not v:
            raise ValueError(f"{label} is needed.")
        out[key] = v
    for k, v in row.items():        # keep what the form does not show (a starter's extra keys)
        if k not in out and k not in ("starter", "own") and not k.startswith("_"):
            out[k] = v
    return out


def _key(kind, row):
    return str(row.get(KINDS[kind]["key"], "")).strip().lower()


def effective(kind):
    """What the screen runs on: starters not put away, the reader's copies in place, then the
    rows the reader added. In the builder's shape."""
    spec = KINDS[kind]
    d = _read(kind)
    hidden = set(d["hidden"])
    own = {_key(kind, r): r for r in d["rows"]}
    out, seen = [], set()
    for s in spec["starter"]():
        k = _key(kind, s)
        if not k or k in hidden:
            continue
        out.append(_nest(kind, own[k]) if k in own else s)
        seen.add(k)
    for r in d["rows"]:
        if _key(kind, r) not in seen:
            out.append(_nest(kind, r))
            seen.add(_key(kind, r))
    return out


def view(kind):
    """The list for the screen's editor: every row with its flags, and the fields."""
    spec = KINDS[kind]
    d = _read(kind)
    hidden = set(d["hidden"])
    own = {_key(kind, r): r for r in d["rows"]}
    rows, seen = [], set()
    starters = spec["starter"]()
    for s in starters:
        k = _key(kind, s)
        if not k or k in hidden:
            continue
        r = dict(own[k]) if k in own else _flat(kind, s)
        r["starter"] = k not in own
        r["own"] = k in own
        rows.append(r)
        seen.add(k)
    for r in d["rows"]:
        if _key(kind, r) not in seen:
            rows.append({**r, "starter": False, "own": True})
    return {"kind": kind, "label": spec["label"], "one": spec["one"], "key": spec["key"], "hint": spec["hint"],
            "fields": [{"key": k, "label": l, "type": t, "required": req} for k, l, t, req in spec["fields"]],
            "rows": rows, "hidden_starters": len([s for s in starters if _key(kind, s) in hidden])}


def save(kind, row, was=""):
    """Add or edit one row. `was` is the key before an edit, when the key itself changed."""
    if kind not in KINDS:
        raise ValueError("no such list")
    row = _clean(kind, row if isinstance(row, dict) else {})
    k = _key(kind, row)
    with _lock:
        d = _read(kind)
        old = (was or "").strip().lower() or k
        d["rows"] = [r for r in d["rows"] if _key(kind, r) not in (k, old)]
        d["rows"].append(row)
        if old != k and old in {_key(kind, s) for s in KINDS[kind]["starter"]()}:
            d["hidden"] = sorted(set(d["hidden"]) | {old})       # the starter it replaced steps aside
        _write(kind, d)
    return row


def remove(kind, key):
    """The reader's row is kept aside so Undo can bring it back; a starter is put away."""
    if kind not in KINDS:
        return {"ok": False, "error": "no such list"}
    key = str(key or "").strip().lower()
    with _lock:
        d = _read(kind)
        mine = [r for r in d["rows"] if _key(kind, r) == key]
        is_starter = key in {_key(kind, s) for s in KINDS[kind]["starter"]()}
        if not mine and not is_starter:
            return {"ok": False, "error": "no such row"}
        undo = ""
        if mine:
            os.makedirs(_previous_dir(), exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S%f")
            undo = f"{kind}-{stamp}.json"
            with open(os.path.join(_previous_dir(), undo), "w", encoding="utf-8") as fh:
                json.dump({"kind": kind, "row": mine[0], "was_starter": is_starter}, fh)
            d["rows"] = [r for r in d["rows"] if _key(kind, r) != key]
        if is_starter:
            d["hidden"] = sorted(set(d["hidden"]) | {key})
        _write(kind, d)
    return {"ok": True, "kind": "own" if mine else "starter", "undo": undo}


def undo_remove(token):
    token = os.path.basename(str(token or ""))
    m = re.match(r"^([a-z]+)-\d{8}-\d{12}\.json$", token)
    if not m or m.group(1) not in KINDS:
        return {"ok": False, "error": "nothing to bring back"}
    kind = m.group(1)
    with _lock:
        p = os.path.join(_previous_dir(), token)
        try:
            with open(p, encoding="utf-8") as fh:
                kept = json.load(fh)
        except (OSError, ValueError):
            return {"ok": False, "error": "that copy is no longer there"}
        row = kept.get("row") or {}
        k = _key(kind, row)
        d = _read(kind)
        d["rows"] = [r for r in d["rows"] if _key(kind, r) != k] + [row]
        d["hidden"] = [h for h in d["hidden"] if h != k]
        _write(kind, d)
        os.remove(p)
    return {"ok": True, "kind": kind, "key": k}


def show_starters(kind):
    if kind not in KINDS:
        return {"ok": False, "error": "no such list"}
    with _lock:
        d = _read(kind)
        d["hidden"] = []
        _write(kind, d)
    return {"ok": True}


def caches_for(kind):
    return KINDS.get(kind, {}).get("caches", [])
