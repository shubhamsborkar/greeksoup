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
import shutil
import threading
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESEARCH_DIR = os.path.join(HERE, "data", "research")


def _vault_from_env():
    """The vault lives in the desk folder unless RESEARCH_DIR in .env points it elsewhere: a folder
    inside a drive the reader already syncs (iCloud Drive, Google Drive, Dropbox, OneDrive,
    Syncthing), which is how the vault reaches a second machine with no service of ours."""
    v = os.path.expanduser((os.getenv("RESEARCH_DIR") or "").strip())
    return v if v and os.path.isabs(v) else DEFAULT_RESEARCH_DIR


RESEARCH_DIR = _vault_from_env()
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
    if kind not in KINDS or (kind == "general" and symbols):
        kind = "stock" if symbols else "general"      # a card that says general but names a listing is about that listing
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


def _subject_folder(symbol="", about=""):
    sym = re.sub(r"[^A-Z0-9.\-]", "", (symbol or "").upper())[:20]
    if sym:
        return sym
    a = re.sub(r"[^a-z0-9]+", "-", (about or "").lower()).strip("-")[:40]
    return a or "general"


def refile(rel, symbol="", about=""):
    """Move an attached file under the subject its note now names, so files/ keeps reading
    like the vault. The index entry moves with it. Returns the new reference, or the old one
    when nothing needed to move or the move was refused."""
    rel = _clean_rel(rel)
    full = file_path(rel) if rel else None
    if not full or not os.path.isfile(full):
        return rel
    want = _subject_folder(symbol, about)
    parts = rel.split("/")
    if len(parts) != 3 or parts[1] == want:
        return rel
    others = [m for m in index().values() if m.get("file") == rel]
    if len(others) > 1:
        return rel                          # two notes share it: leave it where both can see it
    folder = os.path.join(FILES_DIR, want)
    os.makedirs(folder, exist_ok=True)
    stem, ext = os.path.splitext(parts[2])
    fname, k = parts[2], 2
    while os.path.exists(os.path.join(folder, fname)):
        fname, k = f"{stem}-{k}{ext}", k + 1
    new_rel = f"files/{want}/{fname}"
    try:
        os.replace(full, os.path.join(folder, fname))
    except OSError:
        return rel
    old_cache, new_cache = _text_cache_path(rel), _text_cache_path(new_rel)
    try:
        import json
        with open(old_cache, encoding="utf-8") as fh:
            d = json.load(fh)
        d["file"] = new_rel
        with open(new_cache, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
        os.remove(old_cache)
    except (OSError, ValueError):
        pass
    _prune(os.path.dirname(full))
    return new_rel


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
    subject = _subject_folder(symbol, about)
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
    for n in notes.values():             # files start being read in the background as soon as they are seen
        if n["file"]:
            text_of(n["file"])
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


def listing(symbol=None, project=None, ntype=None, tag=None, q=None, kind=None, period=None, about=None, status=None):
    notes = index()
    rows = []
    sym = (symbol or "").upper()
    per = period_key(period) if period else ""
    with_status = {k for k, v in status_all().items() if v.get("status") == (status or "").lower()} if status else None
    for n in notes.values():
        if with_status is not None and not (set(n["symbols"]) & with_status):
            continue
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
        hit = ""
        if q:
            hay = (n["title"] + " " + n["body"] + " " + n["about"] + " " + n["period"] + " "
                   + " ".join(n["tags"]) + " " + " ".join(n["symbols"])).lower()
            if q.lower() not in hay:
                d = _read_text_cache(n["file"]) if n["file"] else None
                if not d or q.lower() not in d.get("text", "").lower():
                    continue
                hit = "file"
        c = card(n)
        if hit:
            c["hit"] = hit
            i = d["text"].lower().find(q.lower())
            c["snippet"] = "…" + re.sub(r"\s+", " ", d["text"][max(0, i - 70):i + 110]).strip() + "…"
        rows.append(c)
    rows.sort(key=lambda r: (not r["pinned"], r["updated"]), reverse=True)
    rows.sort(key=lambda r: not r["pinned"])   # pinned first; within each, newest first
    return rows


def get(note_id):
    n = index().get(note_id)
    if not n:
        return None
    out = card(n, snippet=False)
    out["body"] = n["body"]
    if n["file"]:
        out["text"] = text_status(n["file"])
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
    if kind not in KINDS or (kind == "general" and symbols):
        kind = "stock" if symbols else "general"      # a note that names a listing is about that listing unless it says commodity, sector or macro
    rel = _clean_rel(str(data.get("file") or ""))
    if rel and not (file_path(rel) and os.path.isfile(file_path(rel))):
        raise ValueError("that file is not in the vault's files folder")
    if rel and ntype in ("general", "note"):
        ntype = file_type(rel)          # a file makes the note a document, a model or a clipping unless the reader says otherwise
    if rel:
        rel = refile(rel, symbols[0] if symbols else "", "" if kind == "stock" else str(data.get("about") or ""))
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
    out = get(nid)
    out["new"] = not existing
    return out


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
            _forget_text(n["file"])
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
            _forget_text(rel)
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
    _forget_text(rel)
    _prune(os.path.dirname(full))
    return True


# ---- text from files: read once, kept in index/, so search finds what is inside an annual
# report and the Ask box can read it. Rebuildable from files/ at any time; never the record.
INDEX_DIR = os.path.join(RESEARCH_DIR, "index", "text")
TEXT_CAP = 1_500_000          # characters kept per file; a 300-page annual report is under this
_extract_lock = threading.Lock()
_extracting = set()


def _text_cache_path(rel):
    import hashlib
    return os.path.join(INDEX_DIR, hashlib.sha1(rel.encode("utf-8")).hexdigest() + ".json")


def _read_text_cache(rel):
    try:
        import json
        with open(_text_cache_path(rel), encoding="utf-8") as fh:
            d = json.load(fh)
        full = file_path(rel)
        if full and os.path.isfile(full) and d.get("mtime") == os.path.getmtime(full) and d.get("size") == os.path.getsize(full):
            return d
    except (OSError, ValueError):
        pass
    return None


def _strip_tags(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", html)).strip()


def _xml_text(xml):
    return _strip_tags(xml.replace("</a:p>", "\n").replace("</w:p>", "\n").replace("</p>", "\n"))


def _extract(full):
    """The text inside one file, and how many pages it has. Each reader is small and local;
    a kind of file the desk cannot read yields no text and says so."""
    ext = os.path.splitext(full)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        r = PdfReader(full)
        parts = []
        for i, page in enumerate(r.pages):
            try:
                parts.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 - one bad page never loses the rest
                parts.append("")
            if sum(len(x) for x in parts) > TEXT_CAP:
                break
        return "\n\n".join(parts), len(r.pages), "pdf"
    if ext in (".txt", ".md", ".csv"):
        with open(full, encoding="utf-8", errors="replace") as fh:
            return fh.read(TEXT_CAP), 0, ext[1:]
    if ext in (".html", ".htm"):
        with open(full, encoding="utf-8", errors="replace") as fh:
            return _strip_tags(fh.read(TEXT_CAP * 2))[:TEXT_CAP], 0, "html"
    if ext in (".docx", ".pptx", ".xlsx", ".xlsm"):
        import zipfile
        with zipfile.ZipFile(full) as z:
            names = z.namelist()
            if ext == ".docx":
                return _xml_text(z.read("word/document.xml").decode("utf-8", "replace"))[:TEXT_CAP], 0, "docx"
            if ext == ".pptx":
                slides = sorted(n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n))
                return "\n\n".join(_xml_text(z.read(n).decode("utf-8", "replace")) for n in slides)[:TEXT_CAP], len(slides), "pptx"
            # a spreadsheet: sheet names and the first rows of each, values through the shared strings
            shared = []
            if "xl/sharedStrings.xml" in names:
                shared = [_strip_tags(x) for x in re.findall(r"(?s)<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8", "replace"))]
            wb = z.read("xl/workbook.xml").decode("utf-8", "replace") if "xl/workbook.xml" in names else ""
            sheet_names = re.findall(r'<sheet[^>]*name="([^"]*)"', wb)
            sheets = sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
            out = []
            for i, n in enumerate(sheets):
                title = sheet_names[i] if i < len(sheet_names) else n
                rows = re.findall(r"(?s)<row[^>]*>(.*?)</row>", z.read(n).decode("utf-8", "replace"))[:60]
                lines = []
                for row in rows:
                    cells = []
                    for attrs, inner in re.findall(r"(?s)<c([^>]*)>(.*?)</c>", row):
                        v = re.search(r"<v>(.*?)</v>", inner)
                        val = v.group(1) if v else _strip_tags(inner)
                        if 't="s"' in attrs and val.isdigit() and int(val) < len(shared):
                            val = shared[int(val)]
                        cells.append(val)
                    if any(c.strip() for c in cells):
                        lines.append(" | ".join(cells))
                out.append(f"## {title}\n" + "\n".join(lines))
            return "\n\n".join(out)[:TEXT_CAP], len(sheets), "xlsx"
    return "", 0, "none"


def text_of(rel, wait=False):
    """The text of an attached file from the index, or None while it is still being read.
    With wait=True the file is read now; otherwise a background thread reads it once."""
    rel = _clean_rel(rel)
    full = file_path(rel) if rel else None
    if not full or not os.path.isfile(full):
        return None
    d = _read_text_cache(rel)
    if d:
        return d
    if wait:
        return _extract_now(rel, full)
    with _extract_lock:
        if rel in _extracting:
            return None
        _extracting.add(rel)
    threading.Thread(target=_extract_now, args=(rel, full), daemon=True).start()
    return None


def _extract_now(rel, full):
    import json
    try:
        try:
            text, pages, how = _extract(full)
            err = ""
        except Exception as exc:  # noqa: BLE001
            text, pages, how, err = "", 0, "none", f"{type(exc).__name__}: {exc}"[:200]
        try:
            d = {"file": rel, "mtime": os.path.getmtime(full), "size": os.path.getsize(full),
                 "text": text, "chars": len(text), "pages": pages, "how": how, "error": err,
                 "read_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
            os.makedirs(INDEX_DIR, exist_ok=True)
            tmp = _text_cache_path(rel) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(d, fh)
            os.replace(tmp, _text_cache_path(rel))
        except OSError:
            return None                 # the file went away while it was being read: nothing to keep
        return d
    finally:
        with _extract_lock:
            _extracting.discard(rel)


def text_status(rel):
    """What the reader sees under a file: how many pages and characters were read, or that
    the desk is still reading it, or that this kind of file has no text to read."""
    full = file_path(rel)
    if not full or not os.path.isfile(full):
        return {"state": "missing"}
    d = text_of(rel)
    if d is None:
        return {"state": "reading"}
    if d.get("error"):
        return {"state": "failed", "error": d["error"]}
    if not d.get("chars"):
        return {"state": "none", "how": d.get("how")}
    return {"state": "ready", "chars": d["chars"], "pages": d.get("pages", 0), "how": d.get("how")}


def context(symbol=None, kind=None, about=None, budget=50000):
    """What the reader has written and brought in about one subject, as text for the Ask box:
    the notes' full bodies (newest first) and the text of attached files, cut to a budget."""
    rows = listing(symbol=symbol, kind=kind, about=about)
    notes_out, docs_out, left = [], [], budget
    for r in rows:
        n = index().get(r["id"])
        body = (n["body"] or "").strip()
        if body and left > 0:
            cut = body[:min(len(body), 6000, left)]
            notes_out.append({"title": n["title"], "type": n["type"], "kind": n["kind"], "period": n["period"],
                              "updated": n["updated"], "text": cut + ("…" if len(cut) < len(body) else "")})
            left -= len(cut)
    for r in rows:
        if not r["file"] or left <= 0 or os.path.splitext(r["file"])[1].lower() in IMAGE_EXT:
            continue      # pictures go to the model as pictures (see pictures()), not as text
        d = text_of(r["file"])
        if not d or not d.get("chars"):
            docs_out.append({"title": r["title"], "file": r["file"], "period": r["period"],
                             "text": "" if d else "(the desk is still reading this file; ask again in a moment)"})
            continue
        cut = d["text"][:min(d["chars"], 24000, left)]
        docs_out.append({"title": r["title"], "file": r["file"], "period": r["period"], "pages": d.get("pages", 0),
                         "text": cut + ("…" if len(cut) < d["chars"] else "")})
        left -= len(cut)
    st = status_all().get((symbol or "").upper()) if symbol else None
    pics = [{k: p[k] for k in ("title", "period", "updated", "file")} for p in pictures(symbol=symbol, kind=kind, about=about)]
    return {"subject": symbol or about or kind or "", "notes": notes_out, "documents": docs_out, "pictures": pics,
            "status": ({"status": st["status"], "since": st.get("since", "")} if st and st.get("status") else None),
            "note": "the reader's own notes and files about this subject, from their research vault; quote the note or file by title"}


def pictures(symbol=None, kind=None, about=None, limit=4):
    """The pictures the reader kept on a subject (chart clippings, screenshots), newest first,
    for the Ask box to look at: title, period, and where the file is on this computer."""
    out = []
    for r in listing(symbol=symbol, kind=kind, about=about):
        rel = r.get("file") or ""
        if os.path.splitext(rel)[1].lower() not in IMAGE_EXT or not r.get("file_ok"):
            continue
        full = file_path(rel)
        if not full or not os.path.isfile(full) or os.path.getsize(full) > 5 * 1024 * 1024:
            continue
        out.append({"title": r["title"], "period": r.get("period") or "", "updated": r.get("updated") or "",
                    "file": rel, "path": full,
                    "media_type": {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}.get(os.path.splitext(rel)[1].lower(), "image/png")})
        if len(out) >= limit:
            break
    return out


# ---- status on a name: watchlist, researching, thesis built, invested, exited. Two of the
# five the desk can see for itself (a name on a watch grid; a name in a book); the reader
# sets the rest from the ticker page. Kept in data/research/status.json with every change
# dated, so the journal can read what happened and when.
STATUSES = ["watchlist", "researching", "thesis built", "invested", "exited"]


def _status_path():
    return os.path.join(RESEARCH_DIR, "status.json")


def status_all():
    """Every status the reader set, by symbol: {"AAPL": {"status", "since", "history": [...]}}."""
    try:
        import json
        with open(_status_path(), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def set_status(symbol, status):
    """The reader's word on a name. An empty status clears it (the desk falls back to what it
    can see). Every change is dated and kept, so a status is never overwritten without a trace."""
    import json
    sym = re.sub(r"[^A-Z0-9.\-^=]", "", (symbol or "").upper())[:24]
    status = (status or "").strip().lower()
    if not sym or (status and status not in STATUSES):
        raise ValueError("not a status the desk knows")
    d = status_all()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = d.get(sym) or {"status": "", "since": "", "history": []}
    if entry.get("status") == status:
        return {"symbol": sym, **entry}
    entry["history"] = (entry.get("history") or []) + [{"status": status, "at": now}]
    entry["status"], entry["since"] = status, now[:10]
    d[sym] = entry
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    with _lock:
        tmp = _status_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=2)
        os.replace(tmp, _status_path())
    return {"symbol": sym, **entry}


def status_of(symbol, in_book=False, on_watch=False):
    """What the desk shows for a name: the reader's word if they gave one, else what the desk
    can see (invested when the name is in a book, watchlist when it is on a grid), else nothing."""
    sym = (symbol or "").upper()
    set_ = status_all().get(sym) or {}
    if set_.get("status"):
        return {"symbol": sym, "status": set_["status"], "since": set_.get("since", ""), "set_by": "you", "history": set_.get("history", [])}
    seen = "invested" if in_book else "watchlist" if on_watch else ""
    return {"symbol": sym, "status": seen, "since": "", "set_by": "the desk" if seen else "", "history": set_.get("history", [])}


def timeline(symbol):
    """Everything about one name on a time axis: the notes and documents by period, newest
    first, then by date, and the status changes among them. The proof that nothing was lost."""
    sym = (symbol or "").upper()
    rows = listing(symbol=sym)
    items = []
    for r in rows:
        items.append({"what": "note", "id": r["id"], "title": r["title"], "type": r["type"], "period": r["period"],
                      "date": (r["created"] or r["updated"])[:10], "file": r["file"], "file_ok": r["file_ok"],
                      "project": r["project"], "snippet": r.get("snippet", "")})
    for h in (status_all().get(sym) or {}).get("history", []):
        items.append({"what": "status", "status": h["status"] or "cleared", "date": h["at"][:10], "period": "", "title": ""})
    groups = {}
    for it in items:
        groups.setdefault(it["period"], []).append(it)
    out = []
    for period in sorted(groups, key=lambda p: (p != "", _period_sort(p)), reverse=True):
        rows_ = sorted(groups[period], key=lambda it: it["date"], reverse=True)
        out.append({"period": period, "items": rows_})
    # undated-period items (status changes, notes with no period) come last, by date
    out.sort(key=lambda g: g["period"] == "")
    return {"symbol": sym, "groups": out, "count": len(items)}


# ---- the journal that fills itself. The desk sees the moments that matter (a name enters or
# leaves a book, a status changes, a note or a file is saved, an answer is kept) and writes
# each as a line in one plain file per day, data/research/journal/YYYY-MM-DD.md, with room for
# the reader's one-line why. The reader chooses how: JOURNAL=always writes without asking,
# JOURNAL=ask (the default) holds each moment until the reader says this time or not now,
# JOURNAL=never writes nothing. What the reader did writes itself; what they thought sits
# next to it. It only ever records what happened on the desk, never a view of its own.
DECISIONS = {"status", "book"}


def _journal_dir():
    return os.path.join(RESEARCH_DIR, "journal")


def _pending_path():
    return os.path.join(_journal_dir(), "pending.json")


def journal_mode():
    m = (os.getenv("JOURNAL", "") or "ask").strip().lower()
    return m if m in ("ask", "always", "never") else "ask"


def _read_pending():
    try:
        import json
        with open(_pending_path(), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _write_pending(rows):
    import json
    os.makedirs(_journal_dir(), exist_ok=True)
    tmp = _pending_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    os.replace(tmp, _pending_path())


def journal_event(what, symbol="", text=""):
    """One moment on the desk. Returns what happened to it: written, held for the reader
    (pending), or dropped because the reader said never."""
    import uuid
    entry = {"id": uuid.uuid4().hex[:10], "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
             "what": what, "symbol": (symbol or "").upper()[:24], "text": (text or "").strip()[:300],
             "decision": what in DECISIONS}
    mode = journal_mode()
    if mode == "never" or not entry["text"]:
        return {"mode": mode, "written": False, "pending": None}
    if mode == "always":
        journal_write(entry)
        return {"mode": mode, "written": True, "pending": None, "entry": entry}
    with _lock:
        rows = _read_pending()
        rows.append(entry)
        _write_pending(rows[-200:])
    return {"mode": mode, "written": False, "pending": entry}


def journal_pending():
    return _read_pending()


def journal_decide(entry_id, write, why=""):
    """The reader's answer to a held moment: write it (with a why, if they gave one) or let it go."""
    with _lock:
        rows = _read_pending()
        hit = next((r for r in rows if r.get("id") == entry_id), None)
        if not hit:
            return False
        _write_pending([r for r in rows if r.get("id") != entry_id])
    if write:
        journal_write(hit, why)
    return True


def _day_path(date):
    return os.path.join(_journal_dir(), date + ".md")


def _day_title(date):
    try:
        d = datetime.strptime(date, "%Y-%m-%d")
        return f"Journal, {d.day} {d.strftime('%B %Y')}"
    except ValueError:
        return "Journal, " + date


def journal_write(entry, why=""):
    """Append one line to the day's file, making the file if the day is new."""
    date, time_ = entry["at"][:10], entry["at"][11:16]
    line = f"- {time_} · " + (f"${entry['symbol']} · " if entry.get("symbol") else "") + entry["text"]
    why = re.sub(r"\s+", " ", (why or "").strip())[:500]
    os.makedirs(_journal_dir(), exist_ok=True)
    path = _day_path(date)
    with _lock:
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8") as fh:
            if new:
                fh.write(f'---\ntitle: "{_day_title(date)}"\ntype: journal\ndate: {date}\n---\n')
            fh.write(line + "\n")
            if why:
                fh.write(f"  why: {why}\n")
    return {"date": date, "line": line}


_ENTRY = re.compile(r"^- (\d{2}:\d{2}) · (?:\$([A-Z0-9.\-^=]+) · )?(.*)$")


def journal_days(limit=90):
    """The journal as the reader reads it: days newest first, each with its entries and their whys."""
    d = _journal_dir()
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d), reverse=True):
        if not re.match(r"^\d{4}-\d{2}-\d{2}\.md$", name):
            continue
        date = name[:-3]
        entries = []
        with open(os.path.join(d, name), encoding="utf-8", errors="replace") as fh:
            for i, raw in enumerate(fh):
                line = raw.rstrip("\n")
                m = _ENTRY.match(line)
                if m:
                    entries.append({"line": i, "time": m.group(1), "symbol": m.group(2) or "", "text": m.group(3), "why": ""})
                elif line.startswith("  why: ") and entries:
                    entries[-1]["why"] = line[7:]
                elif line.startswith("  ") and entries and entries[-1]["why"]:
                    entries[-1]["why"] += " " + line.strip()
        out.append({"date": date, "title": _day_title(date), "path": "/".join(("data", "research", "journal", name)), "entries": entries})
        if len(out) >= limit:
            break
    return out


def journal_why(date, line_no, why):
    """Add or replace the why under one entry, by the entry's line in the day's file."""
    path = _day_path(re.sub(r"[^0-9-]", "", date or ""))
    if not os.path.isfile(path):
        return False
    why = re.sub(r"\s+", " ", (why or "").strip())[:500]
    with _lock:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().split("\n")
        if not (0 <= line_no < len(lines)) or not _ENTRY.match(lines[line_no]):
            return False
        j = line_no + 1
        while j < len(lines) and lines[j].startswith("  "):
            j += 1
        lines[line_no + 1:j] = [f"  why: {why}"] if why else []
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    return True


# ---- tasks: from the calendar (results dates for the names the reader holds, watches or
# is researching), from the conversation (Save as task under an answer), and from the
# reader (a line typed anywhere, or a checkbox in any note). One plain list, tasks.md,
# that Obsidian and any editor read; a checkbox in a note stays in that note.
TASK_CATEGORIES = ["results", "filing", "follow-up", "model", "reading", "call", "other"]
_TASK = re.compile(r"^- \[( |x|X)\] (.*)$")
_CHECK = re.compile(r"^(\s*)- \[( |x|X)\] (.+)$")


def _tasks_path():
    return os.path.join(RESEARCH_DIR, "tasks.md")


def _parse_task_line(i, line):
    m = _TASK.match(line)
    if not m:
        return None
    parts = [p.strip() for p in m.group(2).split(" · ")]
    t = {"line": i, "done": m.group(1).lower() == "x", "text": parts[0] if parts else "", "symbol": "", "due": "",
         "category": "", "source": "you", "done_at": ""}
    for p in parts[1:]:
        if re.match(r"^\$[A-Z0-9.\-^=]+$", p):
            t["symbol"] = p[1:]
        elif re.match(r"^due \d{4}-\d{2}-\d{2}$", p):
            t["due"] = p[4:]
        elif re.match(r"^done \d{4}-\d{2}-\d{2}$", p):
            t["done_at"] = p[5:]
        elif p.startswith("via "):
            t["source"] = p[4:]
        elif p.lower() in TASK_CATEGORIES:
            t["category"] = p.lower()
    return t


def _task_line(t):
    bits = [t["text"]]
    if t.get("symbol"):
        bits.append("$" + t["symbol"])
    if t.get("due"):
        bits.append("due " + t["due"])
    if t.get("category"):
        bits.append(t["category"])
    if t.get("source") and t["source"] != "you":
        bits.append("via " + t["source"])
    if t.get("done") and t.get("done_at"):
        bits.append("done " + t["done_at"])
    return f"- [{'x' if t.get('done') else ' '}] " + " · ".join(bits)


def _read_tasks_lines():
    try:
        with open(_tasks_path(), encoding="utf-8", errors="replace") as fh:
            return fh.read().split("\n")
    except OSError:
        return []


def _write_tasks_lines(lines):
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    tmp = _tasks_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines).rstrip("\n") + "\n")
    os.replace(tmp, _tasks_path())


def tasks_all():
    out = []
    for i, line in enumerate(_read_tasks_lines()):
        t = _parse_task_line(i, line)
        if t and t["text"]:
            out.append(t)
    return out


def add_task(text, symbol="", due="", category="", source="you"):
    text = re.sub(r"\s+", " ", (text or "").strip())[:200].replace(" · ", " - ")
    if not text:
        raise ValueError("Write the task first.")
    sym = re.sub(r"[^A-Z0-9.\-^=]", "", (symbol or "").upper())[:24]
    due = due if re.match(r"^\d{4}-\d{2}-\d{2}$", due or "") else ""
    category = (category or "").lower() if (category or "").lower() in TASK_CATEGORIES else ""
    source = re.sub(r"[^\w .:'()-]", "", (source or "you"))[:60] or "you"
    t = {"text": text, "symbol": sym, "due": due, "category": category, "source": source, "done": False}
    with _lock:
        lines = _read_tasks_lines()
        if not lines or not lines[0].startswith("---"):
            lines = ['---', 'title: "Tasks"', 'type: tasks', '---', ''] + lines
        while lines and lines[-1] == "":
            lines.pop()
        lines.append(_task_line(t))
        _write_tasks_lines(lines)
    t["line"] = len(lines) - 1
    return t


def tick_task(line_no, done=True):
    with _lock:
        lines = _read_tasks_lines()
        if not (0 <= line_no < len(lines)):
            return None
        t = _parse_task_line(line_no, lines[line_no])
        if not t:
            return None
        t["done"] = bool(done)
        t["done_at"] = datetime.now().strftime("%Y-%m-%d") if done else ""
        lines[line_no] = _task_line(t)
        _write_tasks_lines(lines)
    return t


def delete_task(line_no):
    with _lock:
        lines = _read_tasks_lines()
        if not (0 <= line_no < len(lines)) or not _TASK.match(lines[line_no]):
            return False
        del lines[line_no]
        _write_tasks_lines(lines)
    return True


def note_tasks():
    """Checkboxes inside notes: each stays in its note, and the desk lists and ticks them there."""
    out = []
    for n in index().values():
        for i, line in enumerate(n["body"].split("\n")):
            m = _CHECK.match(line)
            if m:
                out.append({"note_id": n["id"], "note": n["title"], "symbols": n["symbols"], "project": n.get("project") or "",
                            "line": i, "done": m.group(2).lower() == "x", "text": m.group(3).strip(), "source": "note"})
    return out


def tick_note_task(note_id, line_no, done=True):
    n = index().get(re.sub(r"[^a-z0-9-]", "", (note_id or "").lower()))
    if not n:
        return None
    lines = n["body"].split("\n")
    if not (0 <= line_no < len(lines)):
        return None
    m = _CHECK.match(lines[line_no])
    if not m:
        return None
    lines[line_no] = f"{m.group(1)}- [{'x' if done else ' '}] {m.group(3)}"
    return save({**n, "body": "\n".join(lines)})


def calendar_tasks(rows, tracked=None):
    """Results dates as tasks that made themselves: one per name and date, marked via calendar,
    unless the reader has already ticked or written that one (then the written line stands)."""
    today = datetime.now().strftime("%Y-%m-%d")
    have = {(t["symbol"], t["due"]) for t in tasks_all() if t.get("category") == "results"}
    out, seen = [], set()
    for r in rows or []:
        sym = (r.get("symbol") or r.get("code") or "").upper()
        date = (r.get("date") or "")[:10]
        if not sym or not date or date < today or (sym, date) in have or (sym, date) in seen:
            continue
        if tracked is not None and sym not in tracked:
            continue
        seen.add((sym, date))
        out.append({"line": -1, "done": False, "text": f"{sym} results", "symbol": sym, "due": date,
                    "category": "results", "source": "calendar", "done_at": ""})
    return out


def tasks_view(calendar_rows=None, symbol=None):
    """The list as the reader sees it: open tasks by when they are due (overdue, today, this
    week, later, no date), then the ones done lately."""
    today = datetime.now().date()
    rows = tasks_all() + calendar_tasks(calendar_rows) + [
        {**t, "line": t["line"], "due": "", "category": "", "symbol": (t["symbols"] or [""])[0], "done_at": ""} for t in note_tasks()]
    if symbol:
        sym = symbol.upper()
        rows = [t for t in rows if t.get("symbol") == sym or sym in (t.get("symbols") or [])]
    buckets = {"overdue": [], "today": [], "week": [], "later": [], "undated": []}
    done = []
    for t in rows:
        if t["done"]:
            done.append(t)
            continue
        if not t.get("due"):
            buckets["undated"].append(t)
            continue
        try:
            d = datetime.strptime(t["due"], "%Y-%m-%d").date()
        except ValueError:
            buckets["undated"].append(t)
            continue
        days = (d - today).days
        buckets["overdue" if days < 0 else "today" if days == 0 else "week" if days <= 7 else "later"].append(t)
    for k in buckets:
        buckets[k].sort(key=lambda t: (t.get("due") or "9999", t.get("symbol") or ""))
    done.sort(key=lambda t: t.get("done_at") or "", reverse=True)
    n_open = sum(len(v) for v in buckets.values())
    return {"open": buckets, "done": done[:40], "counts": {"open": n_open, "due": len(buckets["overdue"]) + len(buckets["today"]), "done": len(done)},
            "categories": TASK_CATEGORIES, "path": "/".join(("data", "research", "tasks.md"))}


def tree():
    """The vault as an explorer: a folder per subject (every listing, commodity, sector and
    theme) with everything about it inside, whatever form it came in; then projects, general
    notes, the journal's days, the tasks, and files on no note yet. The folder on disk is
    flat; this is the desk's own view of it, which is the point."""
    notes = index()
    st = status_all()
    def leaf(n):
        return {"id": n["id"], "title": n["title"], "type": n["type"], "period": n["period"], "updated": n["updated"],
                "file": n["file"], "pinned": n["pinned"], "example": n["example"]}
    names, subjects = {}, {}
    general, projects = [], []
    for n in notes.values():
        L = leaf(n)
        if n["type"] == "project":
            projects.append({**L, "symbols": n["symbols"] + n.get("implied_symbols", [])})
        for sym in n["symbols"]:
            names.setdefault(sym, []).append(L)
        if n["kind"] != "stock" and n["about"]:
            subjects.setdefault((n["kind"], n["about"]), []).append(L)
        if not n["symbols"] and not n["about"] and n["type"] != "project":
            general.append(L)
    loose = loose_files()
    loose_by = {}
    for f in loose:
        loose_by.setdefault(f["subject"].upper(), []).append(f)
    def sort_leaves(xs):
        xs.sort(key=lambda L: ((_period_sort(L["period"]) if L["period"] else (-1, 0, "")), L["updated"]), reverse=True)
        return xs
    name_rows = []
    for sym in sorted(set(names) | {k for k in loose_by if re.match(r"^[A-Z0-9.\-^=]+$", k) and k != "GENERAL"}):
        s_ = st.get(sym, {})
        name_rows.append({"symbol": sym, "status": s_.get("status", ""), "notes": sort_leaves(names.get(sym, [])),
                          "loose": loose_by.get(sym, [])})
    subj_rows = {}
    for (kind, about), xs in subjects.items():
        subj_rows.setdefault(kind, []).append({"about": about, "notes": sort_leaves(xs), "loose": loose_by.get(_subject_folder("", about).upper(), [])})
    for kind in subj_rows:
        subj_rows[kind].sort(key=lambda r: r["about"].lower())
    days = journal_days(limit=30)
    try:
        tasks = tasks_view()
    except Exception:  # noqa: BLE001
        tasks = {"counts": {"open": 0, "due": 0}}
    return {"names": name_rows,
            "subjects": [{"kind": k, "rows": subj_rows[k]} for k in ("commodity", "sector", "macro", "general") if k in subj_rows],
            "projects": sorted(projects, key=lambda p: p["title"].lower()),
            "general": sort_leaves(general),
            "journal": [{"date": d["date"], "title": d["title"], "count": len(d["entries"])} for d in days],
            "tasks": tasks["counts"],
            "loose_other": [f for f in loose if f["subject"].upper() not in {r["symbol"] for r in name_rows}
                            and f["subject"].upper() not in {_subject_folder("", r["about"]).upper() for rows in subj_rows.values() for r in rows}],
            "counts": {"notes": sum(1 for n in notes.values() if n["type"] != "project"), "projects": len(projects),
                       "names": len(name_rows), "files": sum(1 for n in notes.values() if n["file"]) + len(loose)}}


# ---- where the vault lives: the desk folder, or a folder the reader already syncs ----
def vault_location():
    return {"path": RESEARCH_DIR, "default": DEFAULT_RESEARCH_DIR, "in_desk": os.path.abspath(RESEARCH_DIR) == os.path.abspath(DEFAULT_RESEARCH_DIR),
            "exists": os.path.isdir(RESEARCH_DIR)}


def _point_at(path):
    """Every path the vault uses follows the root; nothing here is cached at import."""
    global RESEARCH_DIR, NOTES_DIR, FILES_DIR, INDEX_DIR
    RESEARCH_DIR = path
    NOTES_DIR = os.path.join(path, "notes")
    FILES_DIR = os.path.join(path, "files")
    INDEX_DIR = os.path.join(path, "index", "text")
    index(force=True)


def relocate(target):
    """Move the vault to a folder, or adopt the vault already there and fold this one in.
    Rules: a file the target lacks moves across; the same file is dropped here; a file that
    differs stays in the target and the local copy is kept aside under cache/previous, so
    nothing is lost either way. The desk then reads the vault from the new place at once.
    Returns what happened; the caller writes RESEARCH_DIR to .env so it holds after a restart."""
    target = os.path.abspath(os.path.expanduser((target or "").strip()))
    if not target or not os.path.isabs(target):
        raise ValueError("Give the folder's full path.")
    here = os.path.abspath(HERE)
    if target.startswith(os.path.join(here, "cache")) or target == here:
        raise ValueError("Not there: pick a folder outside the desk's own program folder, or the default place inside data.")
    src = os.path.abspath(RESEARCH_DIR)
    if target == src:
        return {"moved": 0, "same": 0, "kept": [], "adopted": False, "path": target}
    os.makedirs(target, exist_ok=True)
    if not os.access(target, os.W_OK):
        raise ValueError("The desk cannot write in that folder.")
    adopted = os.path.isdir(os.path.join(target, "notes")) or os.path.isdir(os.path.join(target, "files"))
    kept_dir = os.path.join(here, "cache", "previous", "vault-move-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    moved, same, kept = 0, 0, []
    if os.path.isdir(src):
        for dirpath, dirs, files in os.walk(src):
            rel_dir = os.path.relpath(dirpath, src)
            if rel_dir.split(os.sep)[0] == "index":
                continue                                   # the index is rebuilt wherever the vault lands
            for f in files:
                if f.startswith(".") or f.endswith(".tmp"):
                    continue
                s_ = os.path.join(dirpath, f)
                rel = os.path.normpath(os.path.join(rel_dir, f))
                d_ = os.path.join(target, rel)
                os.makedirs(os.path.dirname(d_), exist_ok=True)
                if os.path.exists(d_):
                    with open(s_, "rb") as a, open(d_, "rb") as b:
                        if a.read() == b.read():
                            os.remove(s_); same += 1
                            continue
                    k = os.path.join(kept_dir, rel)
                    os.makedirs(os.path.dirname(k), exist_ok=True)
                    shutil.move(s_, k); kept.append(rel.replace(os.sep, "/"))
                    continue
                shutil.move(s_, d_); moved += 1
        shutil.rmtree(src, ignore_errors=True)
    _point_at(target)
    return {"moved": moved, "same": same, "kept": kept, "kept_in": kept_dir if kept else "", "adopted": adopted, "path": target}


def _forget_text(rel):
    try:
        os.remove(_text_cache_path(rel))
    except OSError:
        pass


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
