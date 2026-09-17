"""The reader's own value chains, for the Chain screen.

A chain is a file in the research vault (data/research/chains/<id>.json), so it syncs, backs
up and restores with the notes. The desk ships starters in data/supply_chain.json; they show
until the reader deletes them (hidden, never lost: "Bring the starters back" is the way back)
or edits one, at which point the copy becomes the reader's own.

Shape (format 1): title, region (us | home | global, the quote path), about (one line), layers
ordered upstream to downstream, each with what it buys and sells and the listed names under it,
and edges (named supplier -> customer links). Receipts grade every name and edge: DISCLOSED in a
filing, ON RECORD (the company said it), REPORTED (press only). Status is the reader's tag.

The AI draft: the reader describes the chain; the desk hands the description, the names the
reader holds or watches, and whatever the vault already carries on the subject to the reader's AI
(a key, a local model, or a door) and asks for this shape back. Nothing is saved until the reader
presses Save.
"""
import json
import os
import re
import shutil
import threading
from datetime import datetime

import notes as desk_notes

HERE = os.path.dirname(os.path.abspath(__file__))
STARTERS_PATH = os.path.join(HERE, "data", "supply_chain.json")
FORMAT = 1
MIGRATIONS = {}      # {from_format: fn(dict) -> dict}, one step each; migrate.py runs them at start
STATUSES = ("OWNED", "HOLD", "WATCH", "CHECK", "CONTEXT", "OUT")
RECEIPTS = ("DISCLOSED", "ON RECORD", "REPORTED")
REGIONS = ("us", "home", "global")


def home_id():
    """The home market's id; the desk points this at its own choice (Settings, else the home broker)."""
    import os
    return (os.getenv("HOME_MARKET", "") or "").strip().lower()


def region_of(market):
    """The quote path a country implies: the home market's, the US, or the free feed's global one."""
    market = (market or "").lower()
    if not market:
        return "home"
    if market == home_id():
        return "home"
    return "us" if market == "us" else "global"
_lock = threading.Lock()


# ---- where they live ------------------------------------------------------------------------
def chains_dir():
    return os.path.join(desk_notes.RESEARCH_DIR, "chains")


def _previous_dir():
    return os.path.join(chains_dir(), ".previous")


def _starters_state_path():
    return os.path.join(chains_dir(), ".starters.json")


def _safe_id(cid):
    cid = re.sub(r"[^a-z0-9-]+", "-", str(cid or "").lower()).strip("-")[:60]
    return cid or "chain"


def _path(cid):
    return os.path.join(chains_dir(), _safe_id(cid) + ".json")


# ---- the shape ------------------------------------------------------------------------------
def _s(v, cap=300):
    return str(v if v is not None else "").strip()[:cap]


def _lines(v):
    if isinstance(v, str):
        v = v.splitlines()
    return [_s(x, 400) for x in (v or []) if _s(x, 400)][:40]


def normalise(raw, own=True):
    """One chain in the desk's shape, whatever came in (a starter, the reader's form, the AI's
    draft). Unknown keys drop; bad values fall back; nothing raises on shape."""
    raw = raw if isinstance(raw, dict) else {}
    region = _s(raw.get("region"), 10).lower()
    if region == "in":
        region = "home"
    if region not in REGIONS:
        region = "home"
    # the market is the country the chain is drawn in (any country the desk knows); the region
    # is the quote path it implies, kept beside it so an older chain without a market still prices
    market = _s(raw.get("market"), 8).lower()
    if market:
        region = region_of(market)
    layers = []
    for l in raw.get("layers") or []:
        if not isinstance(l, dict):
            continue
        i = len(layers)
        names = []
        for nm in l.get("names") or []:
            if not isinstance(nm, dict):
                continue
            code = _s(nm.get("code"), 24).upper()
            label = _s(nm.get("label"), 120) or code
            if not label:
                continue
            nreg = _s(nm.get("region"), 10).lower()
            nmarket = _s(nm.get("market"), 8).lower()
            if nmarket:
                nreg = region_of(nmarket)
            status = _s(nm.get("status"), 12).upper()
            receipt = _s(nm.get("receipt"), 12).upper()
            names.append({"code": code, "label": label,
                          "region": nreg if nreg in REGIONS else "", "market": nmarket,
                          "exch": _s(nm.get("exch"), 12).upper(),
                          "status": status if status in STATUSES else "CONTEXT",
                          "receipt": receipt if receipt in RECEIPTS else "REPORTED",
                          "note": _s(nm.get("note"), 600), "source": _s(nm.get("source"), 200)})
        layers.append({"n": i + 1, "name": _s(l.get("name"), 120) or f"Layer {i + 1}",
                       "sells": _s(l.get("sells"), 300), "buys_from": _s(l.get("buys_from"), 300),
                       "sells_to": _s(l.get("sells_to"), 300), "presence": _s(l.get("presence"), 60),
                       "names": names[:60]})
    edges = []
    for e in raw.get("edges") or []:
        if not isinstance(e, dict) or not (_s(e.get("from")) and _s(e.get("to"))):
            continue
        receipt = _s(e.get("receipt"), 12).upper()
        edges.append({"from": _s(e.get("from"), 120), "to": _s(e.get("to"), 120), "what": _s(e.get("what"), 400),
                      "receipt": receipt if receipt in RECEIPTS else "REPORTED", "source": _s(e.get("source"), 200)})
    title = _s(raw.get("title"), 140) or "Untitled chain"
    cid = _safe_id(raw.get("id") or desk_notes.slug(title))
    return {"format": FORMAT, "id": cid, "title": title, "region": region, "market": market, "about": _s(raw.get("about"), 600),
            "as_of": _s(raw.get("as_of"), 20), "source_note": _s(raw.get("source_note"), 400),
            "frame": _lines(raw.get("frame") if raw.get("frame") is not None else raw.get("capex_notes")),
            "hunt": _lines(raw.get("hunt")), "layers": layers[:12], "edges": edges[:80],
            "own": bool(own), "updated": _s(raw.get("updated"), 20)}


# ---- starters -------------------------------------------------------------------------------
def starters():
    try:
        with open(STARTERS_PATH, encoding="utf-8") as fh:
            rows = json.load(fh).get("chains", [])
    except (OSError, ValueError):
        rows = []
    out = []
    for r in rows:
        c = normalise(r, own=False)
        c["starter"] = True
        out.append(c)
    return out


def _hidden_starters():
    try:
        with open(_starters_state_path(), encoding="utf-8") as fh:
            return set(json.load(fh).get("hidden", []))
    except (OSError, ValueError):
        return set()


def _write_hidden(ids):
    os.makedirs(chains_dir(), exist_ok=True)
    with open(_starters_state_path(), "w", encoding="utf-8") as fh:
        json.dump({"hidden": sorted(ids)}, fh, indent=1)


def show_starters():
    """The way back: every starter the reader deleted shows again."""
    with _lock:
        _write_hidden(set())
    return {"ok": True}


# ---- the reader's own ------------------------------------------------------------------------
def own():
    out = []
    d = chains_dir()
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or fn.startswith("."):
            continue
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as fh:
                c = normalise(json.load(fh), own=True)
        except (OSError, ValueError):
            continue
        c["id"] = fn[:-5]
        out.append(c)
    out.sort(key=lambda c: c.get("updated") or "", reverse=True)
    return out


def list_all():
    """The reader's own chains first, then the starters they have not deleted. `hidden` says
    how many starters are put away, so the screen can offer the way back."""
    mine = own()
    taken = {c["id"] for c in mine}
    hidden = _hidden_starters()
    rows = mine + [s for s in starters() if s["id"] not in hidden and s["id"] not in taken]
    return {"chains": rows, "hidden_starters": len([s for s in starters() if s["id"] in hidden and s["id"] not in taken])}


def save(raw):
    """Write one chain into the vault. Saving a starter makes it the reader's own (the starter
    steps aside). Returns the chain as saved."""
    c = normalise(raw, own=True)
    if not c["layers"]:
        raise ValueError("A chain needs at least one layer.")
    c["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.pop("starter", None)
    with _lock:
        os.makedirs(chains_dir(), exist_ok=True)
        with open(_path(c["id"]), "w", encoding="utf-8") as fh:
            json.dump(c, fh, indent=1, ensure_ascii=False)
        if any(s["id"] == c["id"] for s in starters()):
            _write_hidden(_hidden_starters() | {c["id"]})
    return c


def delete(cid):
    """A starter is put away (hidden). The reader's own chain is moved aside under
    chains/.previous so Undo can bring it back. Returns what happened."""
    cid = _safe_id(cid)
    with _lock:
        p = _path(cid)
        if os.path.exists(p):
            os.makedirs(_previous_dir(), exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            kept = os.path.join(_previous_dir(), f"{cid}-{stamp}.json")
            shutil.move(p, kept)
            return {"ok": True, "kind": "own", "undo": os.path.basename(kept)}
        if any(s["id"] == cid for s in starters()):
            _write_hidden(_hidden_starters() | {cid})
            return {"ok": True, "kind": "starter"}
    return {"ok": False, "error": "no such chain"}


def undo_delete(token):
    """The way back for a deleted chain: the kept copy returns to its place."""
    token = os.path.basename(str(token or ""))
    m = re.match(r"^([a-z0-9-]+)-\d{8}-\d{6}\.json$", token)
    if not m:
        return {"ok": False, "error": "nothing to bring back"}
    with _lock:
        kept = os.path.join(_previous_dir(), token)
        if not os.path.exists(kept):
            return {"ok": False, "error": "that copy is no longer there"}
        shutil.move(kept, _path(m.group(1)))
    return {"ok": True, "id": m.group(1)}


# ---- the AI draft ---------------------------------------------------------------------------
DRAFT_SYSTEM = """You build value-chain maps for an equity research desk. The reader describes a chain; you return it as one JSON object and nothing else: no prose, no code fence.

The shape:
{"title": "", "region": "us" | "home" | "global", "about": "one line on what this chain is",
 "frame": ["three to six short lines: what drives the chain, where the money is made, what to watch"],
 "hunt": ["two to five short lines: what the reader should look for next"],
 "layers": [{"name": "", "sells": "what this layer sells", "buys_from": "what it buys, from which layer", "sells_to": "who it sells to, which layer",
             "names": [{"code": "TICKER or empty", "label": "Company", "region": "us" | "home" | "global", "status": "OWNED" | "WATCH" | "CONTEXT", "receipt": "DISCLOSED" | "ON RECORD" | "REPORTED", "note": "one line: what it does in this layer, with a figure if you have one", "source": "where the figure came from"}]}],
 "edges": [{"from": "Company", "to": "Company", "what": "what flows between them", "receipt": "DISCLOSED" | "ON RECORD" | "REPORTED", "source": ""}]}

Rules. Layers run upstream to downstream: raw inputs first, the end customer last; four to eight layers; every layer says what it buys and what it sells, so backward integration and forward integration read off the map. Names are listed companies where they exist, private ones by label with an empty code. Region per name: "us" for a US listing, "home" for the reader's home market, "global" for any other exchange (give the exchange-suffixed symbol, for example 2330.TW). Use a ticker only when you are sure of it; when unsure leave code empty and keep the label. Receipts: DISCLOSED only when a document supplied below states it, and then name that document in source; ON RECORD when the company itself has said it publicly; otherwise REPORTED. Status: OWNED for a name in the reader's book below, WATCH for a name on their watchlists, CONTEXT for everything else. Never invent a figure; a note without a figure is fine. Never tell the reader what to buy, sell or hold."""


def draft_prompt(description, region, held, watched, vault, market_label=""):
    text = "THE READER'S DESCRIPTION\n" + description.strip()
    text += "\n\nHOME MARKET FOR THIS DESK: " + (region or "home")
    if market_label:
        text += "\n\nMARKET THIS CHAIN IS DRAWN IN: " + market_label + " (list the companies of this market at each layer where they exist; a name from elsewhere gets its own region on its row)"
    text += "\n\nNAMES THE READER HOLDS (status OWNED): " + (", ".join(sorted(held)) or "none")
    text += "\nNAMES THE READER WATCHES (status WATCH): " + (", ".join(sorted(watched)) or "none")
    if vault and (vault.get("notes") or vault.get("documents")):
        text += "\n\nWHAT THE READER'S VAULT ALREADY HOLDS ON THIS SUBJECT (their own work; quote a note or file by title)\n"
        text += json.dumps(vault, ensure_ascii=False)[:60000]
    return text


def parse_draft(text):
    """The JSON object out of whatever the model wrote around it."""
    text = (text or "").strip()
    text = re.sub(r"^```[a-z]*\s*|\s*```$", "", text, flags=re.I)
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("no object")
    return json.loads(text[a:b + 1])


def draft(description, region="home", held=(), watched=(), symbol="", about="", door="", ask=None, run_door=None, market_label=""):
    """A first fill of the chain from the reader's words, for the reader to keep or drop line by
    line. `ask(messages, system)` is the desk's AI call; `run_door(name, prompt)` a door."""
    description = (description or "").strip()[:4000]
    if len(description) < 12:
        return {"ok": False, "error": "Describe the chain in a line or two first: the product, the industry, or the company at its centre."}
    vault = None
    try:
        if symbol or about:
            vault = desk_notes.context(symbol=symbol or None, about=about or None, budget=40000)
    except Exception:  # noqa: BLE001
        vault = None
    prompt = draft_prompt(description, region, held, watched, vault, market_label)
    if door and run_door:
        out = run_door(door, DRAFT_SYSTEM + "\n\n" + prompt + "\n\nReturn the JSON object and nothing else. Do not run commands, edit files or ask for permissions.")
        if not out.get("ok"):
            return out
        text = out.get("answer", "")
    else:
        out = ask([{"role": "user", "content": prompt}], DRAFT_SYSTEM)
        if not out.get("ok"):
            return out
        if out.get("refused"):
            return {"ok": False, "error": "The model declined to draft that one."}
        text = out.get("text", "")
    try:
        raw = parse_draft(text)
    except ValueError:
        return {"ok": False, "error": "The model did not answer in the shape the desk reads. Try once more, or describe the chain in fewer words."}
    c = normalise(raw, own=True)
    if not c["layers"]:
        return {"ok": False, "error": "The model sent no layers. Try once more with the product or industry named plainly."}
    c["as_of"] = datetime.now().strftime("%Y-%m-%d")
    c["source_note"] = "Drafted with your AI from your description" + (" and your vault" if vault and (vault.get("notes") or vault.get("documents")) else "") + "; every line is yours to keep, change or drop."
    return {"ok": True, "chain": c}
