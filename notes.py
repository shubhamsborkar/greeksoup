"""The research vault: the research you write and the files you bring in, kept as
plain files in data/research/, and the links between them, the names they are about
and the projects they belong to.

    data/research/
      notes/   one Markdown file per note, flat
      files/   what the reader brings in (annual reports, models, screenshots),
               one folder per subject: files/AAPL/, files/rubber/

One file per note. The first lines are the note's card, the rest is the note:

    ---
    title: "Talabat, second quarter call"
    kind: stock              stock | commodity | sector | macro | general   (what it is about)
    type: concall            general | news | insight | concall | meeting | risk | answer |
                             document | model | clipping | decision | exit | project
    symbols: [TALABAT.AE]    the listings this note is about, Yahoo's symbols
    about: ""                for a commodity, sector or macro note: rubber, Gulf delivery, US rates
    period: "Q2 FY26"        the quarter (or year) being researched, as the reader says it
    file: ""                 a file attached to this note, relative to data/research: files/AAPL/10k.pdf
    project: "Gulf delivery" the project this note belongs to, by the project note's title
    tags: [gulf, delivery]
    pinned: false
    created: 2026-09-15 11:40
    updated: 2026-09-15 11:40
    ---
    The body, in Markdown. [[Another note]] links to a note by its title, and $TALABAT.AE
    names a listing anywhere in the text.

Two axes on the card. `kind` is what the note is about: a listing (stock), a commodity,
a sector, the macro picture, or nothing in particular (general). `type` is what sort of
writing it is: a call, a meeting, a risk, news, an insight, an answer your AI gave that
you chose to keep, a document, a model or a clipping (a note with a file attached), a
decision or an exit (the journal), or a project.

A document is a note with a file attached. The file carries the content and the note
carries the connections: the annual report dropped on Apple's page lives at
files/AAPL/apple-10k-fy25.pdf and its note names $AAPL, takes the period FY25, joins a
project and links to the call note that quotes it, so nothing brought in is ever loose.
Delete the note and the reader is asked about the file; delete the file by hand and the
note says it is missing rather than vanishing. A stock note carries its subject in `symbols`; the other
kinds name theirs in `about`, so "commodity · rubber" and "sector · Gulf delivery" are
subjects the desk can group and filter on like a listing. `period` is the quarter or year
the note is researching, written the way the reader says it (Q2 FY26, H1 FY26, FY26,
Q3 2026); the desk tidies the spacing and case and otherwise keeps the words.

Why one flat folder with a card, rather than a folder per kind: Obsidian resolves
[[links]] by title alone, and its Properties panel and Bases filter on card fields,
so "every commodity note" or "everything on Q2 FY26" is one filter with no folder to keep;
a note is re-filed by editing one line rather than moving a file, so nothing that links
to it breaks; and an agent needs to know exactly one folder. The card is valid YAML
(titles are quoted) so Obsidian reads every field as a property.

A project is a note whose type is project; its symbols are the names in the project.
That is the whole graph: a symbol is connected to every note that names it, a subject to
every note about it, a project to every note that belongs to it and every symbol it
lists, and a note to every note it links to. Open the folder in Obsidian or any editor
and the same files are there; an AI agent reads and writes them like any other file.
Nothing here leaves this computer, and nothing is written here unless the reader saves it.
"""
import os
import re
import threading
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.join(HERE, "data", "research")
NOTES_DIR = os.path.join(RESEARCH_DIR, "notes")
FILES_DIR = os.path.join(RESEARCH_DIR, "files")
LEGACY_NOTES_DIR = os.path.join(HERE, "data", "notes")   # where notes lived before 2026-09-15.11; moved on first scan
TYPES = ["general", "news", "insight", "concall", "meeting", "risk", "answer",
         "document", "model", "clipping", "decision", "exit", "project"]
FILE_TYPES = {".pdf": "document", ".doc": "document", ".docx": "document", ".txt": "document", ".md": "document",
              ".rtf": "document", ".pptx": "document", ".html": "document", ".htm": "document",
              ".xlsx": "model", ".xls": "model", ".xlsm": "model", ".csv": "model", ".numbers": "model", ".ods": "model",
              ".png": "clipping", ".jpg": "clipping", ".jpeg": "clipping", ".gif": "clipping", ".webp": "clipping"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
FILE_CAP = 200 * 1024 * 1024   # one file; an annual report is a few MB, a scan a few tens
KINDS = ["stock", "commodity", "sector", "macro", "general"]
_lock = threading.Lock()
_index = {"at": 0.0, "notes": None}

_WIKI = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
_SYM = re.compile(r"(?<![\w$])\$([A-Z][A-Z0-9]{0,9}(?:[.\-][A-Z0-9]{1,6})?)\b")
_PERIOD = re.compile(r"^(?:(Q[1-4]|H[12])\s*)?(FY|CY)?\s*'?(\d{2}|\d{4})$", re.I)


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return s[:80] or "note"


def period_key(text):
    """The period the way the desk files it: 'q2fy26', '2Q FY 2026', 'Q2 FY26' all become
    Q2 FY26; 'FY26', 'H1 FY26', 'Q3 2026' and 'CY26' keep their own shape. Anything the
    pattern does not recognise is kept as typed, trimmed, so the reader is never corrected."""
    t = re.sub(r"\s+", " ", (text or "").strip())[:40]
    if not t:
        return ""
    s = t.upper().replace(" ", "")
    m = re.match(r"^([1-4])Q(FY|CY)?'?(\d{2}|\d{4})$", s)          # 2QFY26 -> Q2 FY26
    if m:
        s = f"Q{m.group(1)}{m.group(2) or ''}{m.group(3)}"
    m = _PERIOD.match(s)
    if not m:
        return t
    part, basis, year = m.group(1), m.group(2), m.group(3)
    if basis:
        year = year[-2:]
    return " ".join(x for x in (part, (basis or "") + year) if x)


def _q(s):
    """A card value as a YAML double-quoted scalar, so a colon or a hash in a title never breaks the card."""
    return '"' + str(s or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def _unq(v):
    v = (v or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        inner = v[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\") if v[0] == '"' else inner
    return v


def _parse_list(v):
    v = (v or "").strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [_unq(x) for x in v.split(",") if _unq(x)]


def parse(text):
    """Front matter and body. Tolerant: a file with no front matter is a general note titled by
    its first line; a card with no kind is a stock note if it names a listing, general otherwise."""
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
    title = _unq(meta.get("title", ""))
    if not title:
        first = next((l.strip("# ").strip() for l in body.splitlines() if l.strip()), "")
        title = first[:120] or "Untitled"
    ntype = _unq(meta.get("type", "general")).lower()
    if ntype not in TYPES:
        ntype = "general"
    symbols = [s.upper() for s in _parse_list(meta.get("symbols", ""))]
    for s in _SYM.findall(body):
        if s not in symbols:
            symbols.append(s)
    kind = _unq(meta.get("kind", "")).lower()
    if kind not in KINDS:
        kind = "stock" if symbols else "general"
    about = _unq(meta.get("about", ""))[:120]
    if kind == "stock":
        about = ""
    return {
        "title": title, "kind": kind, "type": ntype, "symbols": symbols, "about": about,
        "period": period_key(_unq(meta.get("period", ""))),
        "file": _clean_rel(_unq(meta.get("file", ""))),
        "project": _unq(meta.get("project", "")),
        "tags": [t.lower() for t in _parse_list(meta.get("tags", ""))],
        "pinned": _unq(meta.get("pinned", "false")).lower() in ("true", "yes", "1"),
        "created": _unq(meta.get("created", "")), "updated": _unq(meta.get("updated", "")),
        "links": [t.strip() for t in _WIKI.findall(body)],
        "body": body,
    }


def render(note):
    """The file back from the note: the card, then the body. Every free-text field is quoted
    so the card stays valid YAML and Obsidian shows each field as a property."""
    def lst(xs):
        return "[" + ", ".join(xs) + "]"
    lines = ["---", f"title: {_q(note['title'])}", f"kind: {note.get('kind') or 'general'}", f"type: {note['type']}",
             f"symbols: {lst(note.get('symbols') or [])}",
             f"about: {_q(note.get('about') or '')}",
             f"period: {_q(note.get('period') or '')}",
             f"file: {_q(note.get('file') or '')}",
             f"project: {_q(note.get('project') or '')}",
             f"tags: {lst(note.get('tags') or [])}",
             f"pinned: {'true' if note.get('pinned') else 'false'}",
             f"created: {note.get('created') or ''}", f"updated: {note.get('updated') or ''}", "---", ""]
    return "\n".join(lines) + (note.get("body") or "").rstrip("\n") + "\n"


def migrate():
    """Notes used to live in data/notes. Move them into the vault once, keeping a reader's
    own file over a shipped example of the same name, and leave nothing behind."""
    if not os.path.isdir(LEGACY_NOTES_DIR):
        return 0
    os.makedirs(NOTES_DIR, exist_ok=True)
    moved = 0
    for name in sorted(os.listdir(LEGACY_NOTES_DIR)):
        src = os.path.join(LEGACY_NOTES_DIR, name)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(NOTES_DIR, name)
        if os.path.exists(dst):
            if name.startswith("example-") or open(src, "rb").read() == open(dst, "rb").read():
                os.remove(src)          # the shipped example, or the same file: nothing to keep
                continue
            stem, ext = os.path.splitext(name)
            k = 2
            while os.path.exists(os.path.join(NOTES_DIR, f"{stem}-{k}{ext}")):
                k += 1
            dst = os.path.join(NOTES_DIR, f"{stem}-{k}{ext}")
        os.replace(src, dst)
        moved += 1
    try:
        os.rmdir(LEGACY_NOTES_DIR)
    except OSError:
        pass                            # something else in there; leave it to the reader
    return moved


def _clean_rel(rel):
    """A file reference the way the card holds it: files/<subject>/<name>, forward slashes,
    no way out of the vault. Anything else is dropped."""
    rel = (rel or "").replace("\\", "/").strip().strip("/")
    parts = [p for p in rel.split("/") if p]
    if len(parts) < 2 or parts[0] != "files" or any(p in (".", "..") or p.startswith(".") for p in parts):
        return ""
    return "/".join(parts)[:300]


def file_path(rel):
    """The absolute path of a file reference, or None when it is not inside files/."""
    rel = _clean_rel(rel)
    if not rel:
        return None
    full = os.path.abspath(os.path.join(RESEARCH_DIR, *rel.split("/")))
    if not full.startswith(os.path.abspath(FILES_DIR) + os.sep):
        return None
    return full


def file_type(name):
    """What sort of note a file makes: a document, a model or a clipping, by its extension."""
    return FILE_TYPES.get(os.path.splitext(name or "")[1].lower(), "document")


def store_file(name, data, symbol="", about=""):
    """Put a file the reader brought in under files/<subject>/, with a safe name that never
    overwrites another. Returns the reference the card will hold."""
    if not data:
        raise ValueError("the file is empty")
    if len(data) > FILE_CAP:
        raise ValueError("that file is larger than the desk keeps (200 MB)")
    stem, ext = os.path.splitext(os.path.basename(name or "file"))
    ext = re.sub(r"[^a-z0-9.]", "", ext.lower())[:12]
    stem = slug(stem)[:80] or "file"
    sym = re.sub(r"[^A-Z0-9.\-]", "", (symbol or "").upper())[:20]
    subject = sym or slug(about)[:40] or "general"
    folder = os.path.join(FILES_DIR, subject)
    os.makedirs(folder, exist_ok=True)
    fname, k = stem + ext, 2
    while os.path.exists(os.path.join(folder, fname)):
        fname, k = f"{stem}-{k}{ext}", k + 1
    with open(os.path.join(folder, fname), "wb") as fh:
        fh.write(data)
    return f"files/{subject}/{fname}"


def _scan():
    migrate()
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
        n["path"] = "/".join(("data", "research", "notes", name))
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
    out = {k: n[k] for k in ("id", "title", "kind", "type", "symbols", "about", "period", "project", "project_id",
                             "tags", "pinned", "created", "updated", "link_ids", "backlinks", "example", "path", "file")}
    out["implied_symbols"] = n.get("implied_symbols", [])
    # the attached file is checked as the card is read, so a file moved by hand shows as missing at once
    full = file_path(n["file"]) if n["file"] else None
    out["file_ok"] = bool(full and os.path.isfile(full))
    out["file_size"] = os.path.getsize(full) if out["file_ok"] else 0
    out["file_image"] = bool(n["file"] and os.path.splitext(n["file"])[1].lower() in IMAGE_EXT)
    if snippet:
        text = re.sub(r"\s+", " ", re.sub(r"[#*_>\[\]$`]", "", n["body"])).strip()
        out["snippet"] = text[:180] + ("…" if len(text) > 180 else "")
    return out


def facets():
    """What the folder holds, for the filter chips: the periods and the subjects in use."""
    notes = index()
    periods = sorted({n["period"] for n in notes.values() if n["period"]}, key=_period_sort, reverse=True)
    abouts = sorted({(n["kind"], n["about"]) for n in notes.values() if n["about"]})
    return {"periods": periods, "abouts": [{"kind": k, "about": a} for k, a in abouts]}


def _period_sort(p):
    """Newest period first: the year, then the part of it; anything unrecognised sorts last."""
    m = re.match(r"^(?:(Q[1-4]|H[12]) )?(?:FY|CY)?(\d{2,4})$", p)
    if not m:
        return (-1, 0, p)
    part, year = m.group(1), int(m.group(2))
    if year < 100:
        year += 2000
    frac = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "H1": 2, "H2": 4}.get(part or "", 5)
    return (year, frac, p)


def listing(symbol=None, project=None, ntype=None, tag=None, q=None, kind=None, period=None, about=None):
    notes = index()
    rows = []
    sym = (symbol or "").upper()
    per = period_key(period) if period else ""
    for n in notes.values():
        if sym and sym not in n["symbols"] and not (n["type"] == "project" and sym in n.get("implied_symbols", [])):
            continue
        if project and (n.get("project") or "").lower() != project.lower() and n["title"].lower() != project.lower():
            continue
        if ntype and n["type"] != ntype:
            continue
        if kind and n["kind"] != kind:
            continue
        if per and n["period"] != per:
            continue
        if about and n["about"].lower() != about.lower():
            continue
        if tag and tag.lower() not in n["tags"]:
            continue
        if q:
            hay = (n["title"] + " " + n["body"] + " " + n["about"] + " " + n["period"] + " "
                   + " ".join(n["tags"]) + " " + " ".join(n["symbols"])).lower()
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
    kind = (data.get("kind") or "").lower()
    if kind not in KINDS:
        kind = "stock" if symbols else "general"
    rel = _clean_rel(str(data.get("file") or ""))
    if rel and not (file_path(rel) and os.path.isfile(file_path(rel))):
        raise ValueError("that file is not in the vault's files folder")
    if rel and ntype in ("general", "note"):
        ntype = file_type(rel)          # a file makes the note a document, a model or a clipping unless the reader says otherwise
    note = {"title": title, "kind": kind, "type": ntype, "symbols": symbols, "file": rel,
            "about": "" if kind == "stock" else str(data.get("about") or "").strip()[:120],
            "period": period_key(str(data.get("period") or "")),
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


def delete(note_id, with_file=False):
    """Remove a note. With with_file, its attached file goes too, unless another note still points at it."""
    nid = re.sub(r"[^a-z0-9-]", "", (note_id or "").lower())
    path = os.path.join(NOTES_DIR, nid + ".md")
    if not nid or not os.path.isfile(path):
        return False
    n = index().get(nid) or {}
    with _lock:
        os.remove(path)
    if with_file and n.get("file"):
        others = [m for m in index(force=True).values() if m.get("file") == n["file"]]
        full = file_path(n["file"])
        if not others and full and os.path.isfile(full):
            os.remove(full)
            _prune(os.path.dirname(full))
    index(force=True)
    return True


def detach(note_id, delete_file=False):
    """Take the file off a note; the note stays. With delete_file the file is removed from files/ too."""
    n = index().get(re.sub(r"[^a-z0-9-]", "", (note_id or "").lower()))
    if not n:
        return None
    rel = n.get("file")
    if delete_file and rel:
        full = file_path(rel)
        others = [m for m in index().values() if m.get("file") == rel and m["id"] != n["id"]]
        if not others and full and os.path.isfile(full):
            os.remove(full)
            _prune(os.path.dirname(full))
    return save({**n, "file": ""})


def loose_files():
    """Files in files/ that no note points at: dropped in from Finder, or left behind when a
    note let its file go. Listed so the reader can give each a note or remove it; nothing loose is hidden."""
    if not os.path.isdir(FILES_DIR):
        return []
    held = {n["file"] for n in index().values() if n.get("file")}
    out = []
    for dirpath, _dirs, files in os.walk(FILES_DIR):
        for f in sorted(files):
            if f.startswith("."):
                continue
            full = os.path.join(dirpath, f)
            rel = "files/" + os.path.relpath(full, FILES_DIR).replace(os.sep, "/")
            if rel in held:
                continue
            subject = rel.split("/")[1] if rel.count("/") >= 2 else ""
            out.append({"file": rel, "name": f, "subject": subject, "size": os.path.getsize(full),
                        "type": file_type(f), "modified": datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M")})
    out.sort(key=lambda r: r["modified"], reverse=True)
    return out


def remove_file(rel):
    """Delete a loose file from files/. Refused while any note still points at it."""
    full = file_path(rel)
    if not full or not os.path.isfile(full):
        return False
    if any(n.get("file") == _clean_rel(rel) for n in index(force=True).values()):
        return False
    os.remove(full)
    _prune(os.path.dirname(full))
    return True


def _prune(folder):
    """A subject folder with nothing left in it goes too, so files/ reads like the vault."""
    try:
        if os.path.abspath(folder) != os.path.abspath(FILES_DIR) and not os.listdir(folder):
            os.rmdir(folder)
    except OSError:
        pass


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
        nk = node("project" if n["type"] == "project" else "note", n["id"], n["title"], type=n["type"], about_kind=n["kind"],
                  period=n["period"], updated=n["updated"])
        for s in n["symbols"] + n.get("implied_symbols", []):
            edges.append([nk, node("symbol", s, s)])
        if n["about"]:   # a commodity, sector or theme is a subject like a listing: notes about it connect through it
            edges.append([nk, node("subject", f"{n['kind']}:{n['about'].lower()}", n["about"], subject_kind=n["kind"])])
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
