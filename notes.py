"""Notes: the research you write, kept as plain Markdown files in data/notes/, and
the links between them, the names they are about and the projects they belong to.

One file per note. The first lines are the note's card, the rest is the note:

    ---
    title: Talabat, second quarter call
    type: concall            general | news | insight | concall | meeting | risk | project
    symbols: [TALABAT.AE]    the listings this note is about, Yahoo's symbols
    project: Gulf delivery   the project this note belongs to, by the project note's title
    tags: [gulf, delivery]
    pinned: false
    created: 2026-09-15 11:40
    updated: 2026-09-15 11:40
    ---
    The body, in Markdown. [[Another note]] links to a note by its title, and $TALABAT.AE
    names a listing anywhere in the text.

A project is a note whose type is project; its symbols are the names in the project.
That is the whole graph: a symbol is connected to every note that names it, a project
to every note that belongs to it and every symbol it lists, and a note to every note
it links to. Open the folder in Obsidian or any editor and the same files are there;
an AI agent reads and writes them like any other file. Nothing here leaves this computer.
"""
import os
import re
import threading
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR = os.path.join(HERE, "data", "notes")
TYPES = ["general", "news", "insight", "concall", "meeting", "risk", "project"]
_lock = threading.Lock()
_index = {"at": 0.0, "notes": None}

_WIKI = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
_SYM = re.compile(r"(?<![\w$])\$([A-Z][A-Z0-9]{0,9}(?:[.\-][A-Z0-9]{1,6})?)\b")


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return s[:80] or "note"


def _parse_list(v):
    v = (v or "").strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [x.strip().strip('"').strip("'") for x in v.split(",") if x.strip().strip('"').strip("'")]


def parse(text):
    """Front matter and body. Tolerant: a file with no front matter is a general note titled by its first line."""
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            head, body = text[3:end], text[end + 4:]
            for line in head.splitlines():
                if ":" in line and not line.startswith(" "):
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
    body = body.lstrip("\n")
    title = meta.get("title", "").strip().strip('"')
    if not title:
        first = next((l.strip("# ").strip() for l in body.splitlines() if l.strip()), "")
        title = first[:120] or "Untitled"
    ntype = meta.get("type", "general").strip().lower()
    if ntype not in TYPES:
        ntype = "general"
    symbols = [s.upper() for s in _parse_list(meta.get("symbols", ""))]
    for s in _SYM.findall(body):
        if s not in symbols:
            symbols.append(s)
    return {
        "title": title, "type": ntype, "symbols": symbols,
        "project": meta.get("project", "").strip().strip('"'),
        "tags": [t.lower() for t in _parse_list(meta.get("tags", ""))],
        "pinned": meta.get("pinned", "false").strip().lower() in ("true", "yes", "1"),
        "created": meta.get("created", "").strip(), "updated": meta.get("updated", "").strip(),
        "links": [t.strip() for t in _WIKI.findall(body)],
        "body": body,
    }


def render(note):
    """The file back from the note: the card, then the body."""
    def lst(xs):
        return "[" + ", ".join(xs) + "]"
    lines = ["---", f"title: {note['title']}", f"type: {note['type']}",
             f"symbols: {lst(note.get('symbols') or [])}",
             f"project: {note.get('project') or ''}",
             f"tags: {lst(note.get('tags') or [])}",
             f"pinned: {'true' if note.get('pinned') else 'false'}",
             f"created: {note.get('created') or ''}", f"updated: {note.get('updated') or ''}", "---", ""]
    return "\n".join(lines) + (note.get("body") or "").rstrip("\n") + "\n"


def _scan():
    os.makedirs(NOTES_DIR, exist_ok=True)
    notes = {}
    for name in sorted(os.listdir(NOTES_DIR)):
        if not name.endswith(".md") or name.startswith("."):
            continue
        path = os.path.join(NOTES_DIR, name)
        try:
            n = parse(open(path, encoding="utf-8", errors="replace").read())
        except OSError:
            continue
        n["id"] = name[:-3]
        n["file"] = os.path.join("data", "notes", name)
        n["example"] = name.startswith("example-")
        mtime = os.path.getmtime(path)
        if not n["updated"]:
            n["updated"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        if not n["created"]:
            n["created"] = n["updated"]
        notes[n["id"]] = n
    # backlinks and project membership, resolved by title
    by_title = {n["title"].lower(): n["id"] for n in notes.values()}
    for n in notes.values():
        n["link_ids"] = [by_title[t.lower()] for t in n["links"] if t.lower() in by_title]
        n["backlinks"] = []
    for n in notes.values():
        for lid in n["link_ids"]:
            notes[lid]["backlinks"].append(n["id"])
    projects = {n["title"].lower(): n for n in notes.values() if n["type"] == "project"}
    for n in notes.values():
        p = projects.get((n.get("project") or "").lower())
        n["project_id"] = p["id"] if p else None
        if p and n["type"] != "project":
            for s in n["symbols"]:
                if s not in p["symbols"]:
                    p.setdefault("implied_symbols", []).append(s)
    return notes


def index(force=False):
    with _lock:
        if force or _index["notes"] is None or time.time() - _index["at"] > 15:
            _index["notes"] = _scan()
            _index["at"] = time.time()
        return _index["notes"]


def card(n, snippet=True):
    out = {k: n[k] for k in ("id", "title", "type", "symbols", "project", "project_id", "tags", "pinned",
                             "created", "updated", "link_ids", "backlinks", "example", "file")}
    out["implied_symbols"] = n.get("implied_symbols", [])
    if snippet:
        text = re.sub(r"\s+", " ", re.sub(r"[#*_>\[\]$`]", "", n["body"])).strip()
        out["snippet"] = text[:180] + ("…" if len(text) > 180 else "")
    return out


def listing(symbol=None, project=None, ntype=None, tag=None, q=None):
    notes = index()
    rows = []
    sym = (symbol or "").upper()
    for n in notes.values():
        if sym and sym not in n["symbols"] and not (n["type"] == "project" and sym in n.get("implied_symbols", [])):
            continue
        if project and (n.get("project") or "").lower() != project.lower() and n["title"].lower() != project.lower():
            continue
        if ntype and n["type"] != ntype:
            continue
        if tag and tag.lower() not in n["tags"]:
            continue
        if q:
            hay = (n["title"] + " " + n["body"] + " " + " ".join(n["tags"]) + " " + " ".join(n["symbols"])).lower()
            if q.lower() not in hay:
                continue
        rows.append(card(n))
    rows.sort(key=lambda r: (not r["pinned"], r["updated"]), reverse=True)
    rows.sort(key=lambda r: not r["pinned"])   # pinned first; within each, newest first
    return rows


def get(note_id):
    n = index().get(note_id)
    if not n:
        return None
    out = card(n, snippet=False)
    out["body"] = n["body"]
    return out


def save(data):
    """Write one note. A new note gets a file named from its title; a renamed note keeps its file."""
    title = (data.get("title") or "").strip()[:200]
    if not title:
        raise ValueError("a note needs a title")
    ntype = (data.get("type") or "general").lower()
    if ntype not in TYPES:
        ntype = "general"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    nid = re.sub(r"[^a-z0-9-]", "", (data.get("id") or "").lower())
    existing = index().get(nid) if nid else None
    if not existing:
        base = slug(title)
        nid, k = base, 2
        while os.path.exists(os.path.join(NOTES_DIR, nid + ".md")):
            nid, k = f"{base}-{k}", k + 1
    symbols = []
    for s in (data.get("symbols") or []):
        s = str(s).strip().upper()
        if s and s not in symbols:
            symbols.append(s)
    note = {"title": title, "type": ntype, "symbols": symbols,
            "project": (data.get("project") or "").strip()[:120],
            "tags": [re.sub(r"[^a-z0-9-]", "", str(t).lower())[:40] for t in (data.get("tags") or []) if str(t).strip()],
            "pinned": bool(data.get("pinned")),
            "created": existing["created"] if existing else now, "updated": now,
            "body": str(data.get("body") or "")[:200000]}
    os.makedirs(NOTES_DIR, exist_ok=True)
    with _lock:
        with open(os.path.join(NOTES_DIR, nid + ".md"), "w", encoding="utf-8") as fh:
            fh.write(render(note))
    index(force=True)
    return get(nid)


def delete(note_id):
    nid = re.sub(r"[^a-z0-9-]", "", (note_id or "").lower())
    path = os.path.join(NOTES_DIR, nid + ".md")
    if not nid or not os.path.isfile(path):
        return False
    with _lock:
        os.remove(path)
    index(force=True)
    return True


def graph(symbol=None):
    """Everything connected, or everything connected to one symbol: the notes about it,
    the projects it sits in, and the other names those notes and projects also touch."""
    notes = index()
    sym = (symbol or "").upper()
    nodes, edges = {}, []

    def node(kind, key, label, **extra):
        k = f"{kind}:{key}"
        if k not in nodes:
            nodes[k] = {"id": k, "kind": kind, "key": key, "label": label, **extra}
        return k

    chosen = list(notes.values())
    if sym:
        direct = [n for n in notes.values() if sym in n["symbols"] or sym in n.get("implied_symbols", [])]
        proj_titles = {n["title"].lower() for n in direct if n["type"] == "project"} | {(n.get("project") or "").lower() for n in direct}
        chosen = [n for n in notes.values() if n in direct or n["title"].lower() in proj_titles or (n.get("project") or "").lower() in proj_titles - {""}]
    for n in chosen:
        nk = node("project" if n["type"] == "project" else "note", n["id"], n["title"], type=n["type"], updated=n["updated"])
        for s in n["symbols"] + n.get("implied_symbols", []):
            edges.append([nk, node("symbol", s, s)])
        if n.get("project_id"):
            edges.append([nk, node("project", n["project_id"], notes[n["project_id"]]["title"], type="project")])
        for lid in n["link_ids"]:
            t = notes[lid]
            edges.append([nk, node("project" if t["type"] == "project" else "note", lid, t["title"], type=t["type"])])
    related = sorted({nd["key"] for nd in nodes.values() if nd["kind"] == "symbol" and nd["key"] != sym})
    return {"symbol": sym or None, "nodes": list(nodes.values()), "edges": edges, "related_symbols": related,
            "counts": {"notes": sum(1 for n in notes.values() if n["type"] != "project"),
                       "projects": sum(1 for n in notes.values() if n["type"] == "project"),
                       "symbols": len({s for n in notes.values() for s in n["symbols"]})},
            "folder": NOTES_DIR}
