"""The written contracts, checked without the network.

Every broker file, every market file and the AI presets are held to the shape
their README promises, and the settings whitelist covers every key the template
offers. None of this talks to a broker, a feed or GitHub.
"""
import importlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def test_python_version():
    assert sys.version_info >= (3, 10)


def _modules(package):
    pkg = importlib.import_module(package)
    assert pkg.REGISTRY, f"no {package} registered"
    return {name: importlib.import_module(f"{package}.{name}") for name in pkg.REGISTRY}


def test_every_broker_keeps_the_contract():
    for key, mod in _modules("brokers").items():
        meta = getattr(mod, "META", None)
        assert isinstance(meta, dict), f"{key}: META missing"
        for field in ("label", "where", "region", "fields"):
            assert field in meta, f"{key}: META lacks {field}"
        assert isinstance(meta["fields"], list)
        for f in meta["fields"]:
            assert "env" in f and "label" in f, f"{key}: a field lacks env or label"
        for fn in ("connect", "label", "equity", "funds"):
            assert callable(getattr(mod, fn, None)), f"{key}: {fn}() missing"


def test_no_broker_places_orders():
    forbidden = re.compile(r"place_?order|placeorder|/orders\b|submit_order|order_place", re.I)
    for name in os.listdir(os.path.join(HERE, "brokers")):
        if not name.endswith(".py") or name == "__init__.py":
            continue
        text = open(os.path.join(HERE, "brokers", name), encoding="utf-8").read()
        hits = [m.group(0) for m in forbidden.finditer(text)]
        assert not hits, f"brokers/{name} mentions an order path: {hits}"


def test_every_market_keeps_the_contract():
    for key, mod in _modules("markets").items():
        meta = getattr(mod, "META", None)
        assert isinstance(meta, dict), f"{key}: META missing"
        for field in ("id", "label", "currency", "exchanges", "benchmark"):
            assert field in meta, f"{key}: META lacks {field}"
        for fn in ("is_open", "ysym"):
            assert callable(getattr(mod, fn, None)), f"{key}: {fn}() missing"


def test_ai_presets_have_a_shape():
    ai = importlib.import_module("ai")
    assert len(ai.PROVIDERS) >= 14
    for key, p in ai.PROVIDERS.items():
        assert p.get("format") in ("openai", "anthropic"), f"{key}: format"
        assert p.get("label"), f"{key}: label"


def test_env_template_is_whitelisted():
    settings = importlib.import_module("settings")
    allowed = set(settings.ALLOWED)
    for mod in _modules("brokers").values():
        for f in mod.META.get("fields", []):
            allowed.add(f["env"])
    keys = set()
    for line in open(os.path.join(HERE, ".env.example"), encoding="utf-8"):
        line = line.strip()
        m = re.match(r"^#?\s*([A-Z][A-Z0-9_]+)=", line)
        if m:
            keys.add(m.group(1))
    # set by the installer or by hand, on purpose not on the Settings screen
    hand_edited = {"DESK_PORT", "VAULT_OUTPUT_DIR"}
    missing = sorted(k for k in keys if k not in allowed and k not in hand_edited)
    assert not missing, f"keys in .env.example the Settings screen cannot write: {missing}"


def test_version_and_manifest_agree():
    updater = importlib.import_module("updater")
    releases = updater.local_releases()
    assert releases and releases[0].get("version")
    manifest = json.load(open(os.path.join(HERE, "MANIFEST.json"), encoding="utf-8"))
    assert manifest.get("version") == releases[0]["version"], "MANIFEST.json is behind VERSION; run scripts/make_manifest.py"
    for must in ("server.py", "updater.py", "settings.py", "ai.py"):
        assert must in manifest["files"], f"{must} not in the manifest"


def test_ask_box_reads_every_screen_in_the_sidebar():
    """Every screen the sidebar offers can answer a question about itself."""
    server = importlib.import_module("server")
    js = open(os.path.join(HERE, "web", "assets", "desk.js"), encoding="utf-8").read()
    tabs = js.split("const TABS = [", 1)[1].split("\n  ];", 1)[0]
    hrefs = set(re.findall(r'\[\s*"(/[^"]*)"', tabs))
    for href in hrefs:
        page = href.split("?", 1)[0]
        assert page in server.ASK_READS, f"the Ask box has no reads for {page}"


def test_ask_box_reads_real_endpoints():
    server = importlib.import_module("server")
    source = open(os.path.join(HERE, "server.py"), encoding="utf-8").read()
    for label, reads in server.ASK_READS.values():
        assert label
        for ep in reads:
            path = ep.split("?", 1)[0]
            assert f'"{path}"' in source, f"{path} is not an address this desk answers"


def test_ask_box_never_advises():
    """The Ask box describes; it does not tell the reader what to do."""
    ai = importlib.import_module("ai")
    s = ai.ASK_SYSTEM.lower()
    assert "never tell the reader what to buy, sell or hold" in s
    assert "say so plainly instead of guessing" in s
    assert "never invent a figure" in s


def test_slim_shortens_a_long_series_and_can_drop_the_bulky_keys():
    server = importlib.import_module("server")
    card = {"label": "Natural rubber", "value": 241.5,
            "full": [[f"2020-01-{i:02d}", i * 1.5] for i in range(1, 400)],
            "note": "x" * 900, "names": [{"code": "GT", "intensity": "y" * 900}]}
    slim = server._slim(card)
    assert slim["value"] == 241.5 and slim["label"] == "Natural rubber"
    assert len(slim["full"]) == 13, "a long series keeps its first and last few points"
    assert slim["full"][0] == card["full"][0] and slim["full"][-1] == card["full"][-1]
    assert len(slim["note"]) < 200, "a long sentence is cut"
    hard = server._slim(card, server.BULKY)
    assert "full" not in hard and "note" not in hard
    assert "intensity" not in hard["names"][0]
    assert len(json.dumps(hard)) < len(json.dumps(server._slim(card)))


def test_ask_says_what_is_missing_before_it_asks_anything():
    """With nothing set, the Ask box explains rather than reaching the network."""
    ai = importlib.import_module("ai")
    keep = {k: os.environ.get(k) for k in ("AI_PROVIDER", "AI_API_KEY", "AI_MODEL", "AI_BASE_URL", "AI_FORMAT")}
    try:
        for k in keep:
            os.environ.pop(k, None)
        out = ai.ask("what is on this screen?", "Commodities", "{}")
        assert out["ok"] is False and "provider" in out["error"].lower()
        os.environ["AI_PROVIDER"] = "openai"
        assert "key" in (ai.not_ready(ai.settings()) or "").lower()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_windows_scripts_have_no_drive_qualified_variables():
    """PowerShell reads "$name:" as a drive, so a variable followed by a colon inside a
    string is a parse error that stops the whole script. It cost one Windows run."""
    for name in ("install.ps1", "desk-service.ps1", "desk-stop.ps1", "desk-autostart.ps1", os.path.join("docs", "install.ps1"),
                 os.path.join("scripts", "windows_smoke.ps1")):
        path = os.path.join(HERE, name)
        if not os.path.isfile(path):
            continue
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            for m in re.finditer(r"\$([A-Za-z_][A-Za-z0-9_]*):", line):
                if m.group(1).lower() == "env":
                    continue
                if line[m.end():m.end() + 2] == "//":
                    continue
                raise AssertionError(
                    f"{name}:{i} writes ${m.group(1)}: which PowerShell reads as a drive; write ${{{m.group(1)}}}: instead")


def test_docs_nav_points_at_real_pages():
    nav = json.load(open(os.path.join(HERE, "site", "nav.json"), encoding="utf-8"))
    for sec in nav["sections"]:
        for page in sec["pages"]:
            path = os.path.join(HERE, "site", sec["dir"], page + ".md")
            assert os.path.isfile(path), f"docs page missing: {path}"


def test_notes_parse_render_and_links(tmp_path):
    """A note round-trips through its file, names a listing from the body, and the
    folder's links, backlinks and project membership resolve by title."""
    import notes as desk_notes
    n = desk_notes.parse("---\ntitle: One\ntype: concall\nsymbols: [AAPL]\nproject: P\ntags: [x]\n---\nSee [[Two]] and $MSFT.")
    assert n["symbols"] == ["AAPL", "MSFT"] and n["links"] == ["Two"] and n["type"] == "concall"
    again = desk_notes.parse(desk_notes.render({**n, "created": "c", "updated": "u"}))
    assert again["title"] == "One" and again["symbols"] == ["AAPL", "MSFT"] and again["project"] == "P"
    old_dir = desk_notes.NOTES_DIR
    desk_notes.NOTES_DIR = str(tmp_path)
    try:
        (tmp_path / "p.md").write_text("---\ntitle: P\ntype: project\nsymbols: [AAPL]\n---\nproject", encoding="utf-8")
        (tmp_path / "one.md").write_text("---\ntitle: One\ntype: risk\nsymbols: [MSFT]\nproject: P\n---\nlinks [[P]]", encoding="utf-8")
        idx = desk_notes.index(force=True)
        assert idx["one"]["project_id"] == "p" and "one" in idx["p"]["backlinks"]
        g = desk_notes.graph("AAPL")
        assert "MSFT" in g["related_symbols"]          # connected through the project
        assert {r["id"] for r in desk_notes.listing(symbol="MSFT")} == {"one", "p"}   # the note, and the project it joins
    finally:
        desk_notes.NOTES_DIR = old_dir
        desk_notes.index(force=True)


def test_notes_kind_period_and_subject(tmp_path):
    """The card's two axes: kind (what it is about) with a subject for the non-stock kinds,
    and the period being researched, tidied to one shape. A title with a colon survives
    the file, and the listing filters on kind, period and subject."""
    import notes as desk_notes
    assert desk_notes.period_key("q2fy26") == "Q2 FY26" == desk_notes.period_key("2Q FY 2026")
    assert desk_notes.period_key("h1 fy26") == "H1 FY26" and desk_notes.period_key("fy2026") == "FY26"
    assert desk_notes.period_key("Q3 2026") == "Q3 2026" and desk_notes.period_key("Dec 2025 quarter") == "Dec 2025 quarter"
    n = desk_notes.parse(desk_notes.render({"title": 'Rubber: the "Q2" read', "kind": "commodity", "type": "insight",
                                            "about": "Rubber", "period": "q2fy26", "symbols": [], "body": "x"}))
    assert n["title"] == 'Rubber: the "Q2" read' and n["kind"] == "commodity" and n["about"] == "Rubber" and n["period"] == "Q2 FY26"
    assert desk_notes.parse("---\ntitle: T\nsymbols: [AAPL]\n---\nb")["kind"] == "stock"      # no kind on the card: a listing makes it a stock note
    assert desk_notes.parse("---\ntitle: T\n---\nb")["kind"] == "general"
    assert desk_notes.parse("---\ntitle: T\nkind: stock\nabout: x\nsymbols: [AAPL]\n---\nb")["about"] == ""   # a stock note's subject is its symbols
    old_dir = desk_notes.NOTES_DIR
    desk_notes.NOTES_DIR = str(tmp_path)
    try:
        desk_notes.save({"title": "Rubber Q2", "kind": "commodity", "about": "rubber", "period": "Q2 FY26", "type": "insight", "body": "a"})
        desk_notes.save({"title": "Rubber Q1", "kind": "commodity", "about": "rubber", "period": "q1 fy26", "type": "insight", "body": "b"})
        desk_notes.save({"title": "Rates", "kind": "macro", "about": "US rates", "period": "Q2 FY26", "type": "answer", "body": "c"})
        desk_notes.save({"title": "Apple call", "symbols": ["AAPL"], "period": "Q2 FY26", "type": "concall", "body": "d"})
        assert {r["title"] for r in desk_notes.listing(kind="commodity")} == {"Rubber Q2", "Rubber Q1"}
        assert {r["title"] for r in desk_notes.listing(period="q2fy26")} == {"Rubber Q2", "Rates", "Apple call"}
        assert {r["title"] for r in desk_notes.listing(kind="commodity", about="Rubber")} == {"Rubber Q2", "Rubber Q1"}
        assert desk_notes.listing(symbol="AAPL")[0]["kind"] == "stock"
        f = desk_notes.facets()
        assert f["periods"] == ["Q2 FY26", "Q1 FY26"] and {"kind": "macro", "about": "US rates"} in f["abouts"]
        g = desk_notes.graph()
        assert any(nd["kind"] == "subject" and nd["label"] == "rubber" for nd in g["nodes"])
        assert sum(1 for e in g["edges"] if e[1] == "subject:commodity:rubber") == 2   # both rubber notes hang off one subject
    finally:
        desk_notes.NOTES_DIR = old_dir
        desk_notes.index(force=True)


def test_research_vault_files(tmp_path):
    """The vault: notes move from data/notes into data/research/notes once; a file the reader
    brings in lands under files/<subject>/ with a safe name, never outside the vault; a note
    with a file becomes a document, model or clipping by extension; detach keeps or deletes
    the file, and deleting the note can take the file with it."""
    import notes as desk_notes
    keep = (desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR)
    desk_notes.RESEARCH_DIR = str(tmp_path / "research")
    desk_notes.NOTES_DIR = str(tmp_path / "research" / "notes")
    desk_notes.FILES_DIR = str(tmp_path / "research" / "files")
    desk_notes.LEGACY_NOTES_DIR = str(tmp_path / "notes")
    try:
        (tmp_path / "notes").mkdir()
        (tmp_path / "notes" / "old.md").write_text("---\ntitle: Old\n---\nfrom before", encoding="utf-8")
        idx = desk_notes.index(force=True)
        assert "old" in idx and not (tmp_path / "notes").exists()            # moved, and the old folder is gone
        assert (tmp_path / "research" / "notes" / "old.md").exists()
        # bringing a file in
        rel = desk_notes.store_file("Apple 10-K FY25 (final).pdf", b"%PDF-1.4 x", symbol="AAPL")
        assert rel == "files/AAPL/apple-10-k-fy25-final.pdf"
        rel2 = desk_notes.store_file("Apple 10-K FY25 (final).pdf", b"%PDF-1.4 y", symbol="AAPL")
        assert rel2 == "files/AAPL/apple-10-k-fy25-final-2.pdf"                # never overwrites
        assert desk_notes.store_file("q2.xlsx", b"x", about="Gulf delivery").startswith("files/gulf-delivery/")
        assert desk_notes.file_type("a.xlsx") == "model" and desk_notes.file_type("a.PNG") == "clipping" and desk_notes.file_type("a.pdf") == "document"
        assert desk_notes.file_path("../../etc/passwd") is None and desk_notes.file_path("files/../notes/old.md") is None
        assert desk_notes.file_path("notes/old.md") is None
        # the note that carries the file
        n = desk_notes.save({"title": "Apple annual report", "symbols": ["AAPL"], "period": "FY25", "file": rel, "body": ""})
        assert n["type"] == "document" and n["file"] == rel and n["file_ok"] and n["file_size"] == 10
        try:
            desk_notes.save({"title": "Bad", "file": "files/AAPL/not-there.pdf"})
            assert False, "a file that is not in the vault must be refused"
        except ValueError:
            pass
        # the file follows its note's subject: rename the note's name and the file moves, index entry with it
        moved = desk_notes.save({**desk_notes.get(n["id"]), "symbols": ["MSFT"]})
        assert moved["file"] == "files/MSFT/apple-10-k-fy25-final.pdf" and moved["file_ok"] and not (tmp_path / "research" / "files" / "AAPL" / "apple-10-k-fy25-final.pdf").exists()
        gen = desk_notes.save({**moved, "kind": "general", "symbols": []})
        assert gen["kind"] == "general" and gen["file"] == "files/general/apple-10-k-fy25-final.pdf"   # no names: general, and the file follows
        rel = gen["file"]
        assert desk_notes.save({"title": "Named", "kind": "general", "symbols": ["AAPL"]})["kind"] == "stock"   # a name makes it a stock note
        # a missing file is reported, never dropped
        (tmp_path / "research" / rel).unlink()
        assert desk_notes.get(n["id"])["file_ok"] is False and desk_notes.get(n["id"])["file"] == rel
        # detach keeps the note; delete with the file removes it and the emptied subject folder
        n2 = desk_notes.save({"title": "Second", "symbols": ["AAPL"], "file": rel2})
        assert desk_notes.detach(n["id"])["file"] == ""
        assert desk_notes.delete(n2["id"], with_file=True) and not (tmp_path / "research" / rel2).exists()
        assert not (tmp_path / "research" / "files" / "AAPL").exists()
        assert (tmp_path / "research" / "files" / "gulf-delivery").exists()
        # a file no note points at is listed, never hidden; it can be removed only while loose
        loose = desk_notes.loose_files()
        assert [f["file"] for f in loose] == ["files/gulf-delivery/q2.xlsx"] and loose[0]["type"] == "model"
        n3 = desk_notes.save({"title": "Gulf model", "kind": "sector", "about": "Gulf delivery", "file": "files/gulf-delivery/q2.xlsx"})
        assert desk_notes.loose_files() == [] and desk_notes.remove_file("files/gulf-delivery/q2.xlsx") is False
        desk_notes.detach(n3["id"])
        assert desk_notes.remove_file("files/gulf-delivery/q2.xlsx") and not (tmp_path / "research" / "files" / "gulf-delivery").exists()
    finally:
        desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR = keep
        desk_notes.index(force=True)


def _tiny_pdf(text):
    content = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return out


def _tiny_xlsx():
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook><sheets><sheet name="Revenue" sheetId="1"/></sheets></workbook>')
        z.writestr("xl/sharedStrings.xml", "<sst><si><t>Segment</t></si><si><t>Services</t></si></sst>")
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>2025</v></c></row>'
                                               '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2"><v>96169</v></c></row></sheetData></worksheet>')
    return buf.getvalue()


def test_research_text_search_and_context(tmp_path):
    """Text is read out of attached files into the index: a PDF by page, a spreadsheet by
    sheet and row, a Word file by paragraph. Search then finds a phrase that lives only inside
    a file, and the Ask box's context carries the notes' bodies and the files' text under a budget."""
    import io
    import zipfile
    import notes as desk_notes
    keep = (desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR, desk_notes.INDEX_DIR)
    desk_notes.RESEARCH_DIR = str(tmp_path / "research")
    desk_notes.NOTES_DIR = str(tmp_path / "research" / "notes")
    desk_notes.FILES_DIR = str(tmp_path / "research" / "files")
    desk_notes.LEGACY_NOTES_DIR = str(tmp_path / "notes")
    desk_notes.INDEX_DIR = str(tmp_path / "research" / "index" / "text")
    try:
        pdf = desk_notes.store_file("Apple 10-K.pdf", _tiny_pdf("Services revenue grew eleven percent"), symbol="AAPL")
        xl = desk_notes.store_file("model.xlsx", _tiny_xlsx(), symbol="AAPL")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<w:document><w:body><w:p><w:r><w:t>Call transcript: guidance held</w:t></w:r></w:p></w:body></w:document>")
        dx = desk_notes.store_file("call.docx", buf.getvalue(), symbol="AAPL")
        d = desk_notes.text_of(pdf, wait=True)
        assert d["pages"] == 1 and "eleven percent" in d["text"]
        assert desk_notes.text_of(pdf) is d or desk_notes.text_of(pdf)["chars"] == d["chars"]   # from the index the second time
        x = desk_notes.text_of(xl, wait=True)
        assert "## Revenue" in x["text"] and "Services | 96169" in x["text"] and x["pages"] == 1
        assert "guidance held" in desk_notes.text_of(dx, wait=True)["text"]
        assert desk_notes.text_status(pdf)["state"] == "ready" and desk_notes.text_status("files/AAPL/none.pdf")["state"] == "missing"
        desk_notes.save({"title": "Apple annual report", "symbols": ["AAPL"], "period": "FY25", "file": pdf, "body": "the filing"})
        desk_notes.save({"title": "Apple model", "symbols": ["AAPL"], "file": xl, "body": ""})
        desk_notes.save({"title": "Apple thoughts", "symbols": ["AAPL"], "type": "insight", "body": "Services is the story now."})
        hits = desk_notes.listing(q="eleven percent")
        assert [h["title"] for h in hits] == ["Apple annual report"] and hits[0]["hit"] == "file" and "eleven percent" in hits[0]["snippet"]
        assert [h["title"] for h in desk_notes.listing(q="Services")] and len(desk_notes.listing(q="Services")) == 3   # note body, sheet cell, pdf
        c = desk_notes.context(symbol="AAPL")
        assert {n["title"] for n in c["notes"]} == {"Apple annual report", "Apple thoughts"}   # the model has no body
        assert {d["title"] for d in c["documents"]} == {"Apple annual report", "Apple model"}
        assert any("eleven percent" in d["text"] for d in c["documents"])
        small = desk_notes.context(symbol="AAPL", budget=40)
        assert sum(len(n["text"]) for n in small["notes"]) <= 40 and all(d["text"] == "" or d["text"].startswith("(") or len(d["text"]) <= 41 for d in small["documents"])
    finally:
        desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR, desk_notes.INDEX_DIR = keep
        desk_notes.index(force=True)


def test_research_status_and_timeline(tmp_path):
    """Status on a name: the reader's word wins, every change is dated and kept, an empty
    status clears it and the desk falls back to what it can see (a book, a grid). The
    timeline groups everything about the name by period, newest first, status changes included."""
    import notes as desk_notes
    keep = (desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR, desk_notes.INDEX_DIR)
    desk_notes.RESEARCH_DIR = str(tmp_path / "research")
    desk_notes.NOTES_DIR = str(tmp_path / "research" / "notes")
    desk_notes.FILES_DIR = str(tmp_path / "research" / "files")
    desk_notes.LEGACY_NOTES_DIR = str(tmp_path / "notes")
    desk_notes.INDEX_DIR = str(tmp_path / "research" / "index" / "text")
    try:
        assert desk_notes.status_of("AAPL", in_book=True)["status"] == "invested" and desk_notes.status_of("AAPL", on_watch=True)["status"] == "watchlist"
        assert desk_notes.status_of("AAPL")["status"] == ""
        st = desk_notes.set_status("aapl", "researching")
        assert st["symbol"] == "AAPL" and st["status"] == "researching" and len(st["history"]) == 1
        assert desk_notes.status_of("AAPL", in_book=True)["status"] == "researching"       # the reader's word wins over the book
        desk_notes.set_status("AAPL", "thesis built")
        desk_notes.set_status("AAPL", "thesis built")                                      # the same again writes nothing
        assert len(desk_notes.status_all()["AAPL"]["history"]) == 2
        try:
            desk_notes.set_status("AAPL", "bought")
            assert False
        except ValueError:
            pass
        desk_notes.save({"title": "Q2 call", "symbols": ["AAPL"], "period": "Q2 FY26", "type": "concall", "body": "x"})
        desk_notes.save({"title": "Q1 call", "symbols": ["AAPL"], "period": "Q1 FY26", "type": "concall", "body": "y"})
        desk_notes.save({"title": "Loose thought", "symbols": ["AAPL"], "body": "z"})
        assert [r["title"] for r in desk_notes.listing(status="thesis built")] == ["Loose thought", "Q1 call", "Q2 call"] or len(desk_notes.listing(status="thesis built")) == 3
        assert desk_notes.listing(status="exited") == []
        tl = desk_notes.timeline("AAPL")
        assert [g["period"] for g in tl["groups"]] == ["Q2 FY26", "Q1 FY26", ""]
        last = tl["groups"][-1]["items"]
        assert {it["what"] for it in last} == {"note", "status"} and tl["count"] == 5
        desk_notes.set_status("AAPL", "")
        assert desk_notes.status_of("AAPL", in_book=True)["status"] == "invested" and len(desk_notes.status_all()["AAPL"]["history"]) == 3
    finally:
        desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR, desk_notes.INDEX_DIR = keep
        desk_notes.index(force=True)


def test_research_journal(tmp_path, monkeypatch):
    """The journal that fills itself: in ask mode a moment is held until the reader decides,
    in always mode it is written at once with the reader's why beside it, in never mode
    nothing is written; the day's file is plain Markdown the desk reads back, and a why can
    be added or changed under any entry afterwards."""
    import notes as desk_notes
    keep = (desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR, desk_notes.INDEX_DIR)
    desk_notes.RESEARCH_DIR = str(tmp_path / "research")
    desk_notes.NOTES_DIR = str(tmp_path / "research" / "notes")
    desk_notes.FILES_DIR = str(tmp_path / "research" / "files")
    desk_notes.LEGACY_NOTES_DIR = str(tmp_path / "notes")
    desk_notes.INDEX_DIR = str(tmp_path / "research" / "index" / "text")
    try:
        monkeypatch.setenv("JOURNAL", "ask")
        r = desk_notes.journal_event("status", "aapl", "status set to researching")
        assert r["pending"] and r["pending"]["decision"] and not r["written"]
        assert [p["id"] for p in desk_notes.journal_pending()] == [r["pending"]["id"]]
        assert desk_notes.journal_days() == []                               # held, not written
        assert desk_notes.journal_decide(r["pending"]["id"], True, "the quarter changed my mind")
        assert desk_notes.journal_pending() == []
        days = desk_notes.journal_days()
        assert len(days) == 1 and days[0]["entries"][0]["symbol"] == "AAPL" and days[0]["entries"][0]["why"] == "the quarter changed my mind"
        monkeypatch.setenv("JOURNAL", "always")
        r2 = desk_notes.journal_event("note", "AAPL", 'call note saved: "Q2 call"')
        assert r2["written"] and r2["pending"] is None
        monkeypatch.setenv("JOURNAL", "never")
        assert desk_notes.journal_event("book", "AAPL", "added to Desk · Book")["written"] is False and desk_notes.journal_pending() == []
        days = desk_notes.journal_days()
        assert [e["text"] for e in days[0]["entries"]] == ["status set to researching", 'call note saved: "Q2 call"']
        text = open(tmp_path / "research" / "journal" / (days[0]["date"] + ".md"), encoding="utf-8").read()
        assert text.startswith("---\ntitle: \"Journal, ") and "\n  why: the quarter changed my mind\n" in text
        second = days[0]["entries"][1]
        assert desk_notes.journal_why(days[0]["date"], second["line"], "wrote it up the same evening")
        assert desk_notes.journal_days()[0]["entries"][1]["why"] == "wrote it up the same evening"
        assert desk_notes.journal_why(days[0]["date"], second["line"], "")            # a why can be taken away
        assert desk_notes.journal_days()[0]["entries"][1]["why"] == ""
        assert desk_notes.journal_days()[0]["entries"][0]["why"] == "the quarter changed my mind"   # the other entry untouched
    finally:
        desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR, desk_notes.INDEX_DIR = keep
        desk_notes.index(force=True)


def test_research_tasks(tmp_path, monkeypatch):
    """Tasks: a line in tasks.md with its name, due date, category and source; ticked with the
    day it was done; a checkbox inside a note is listed and ticked in that note; a results date
    from the calendar becomes a task on its own, once, and stays ticked once the reader ticks it;
    the view buckets by when things are due."""
    from datetime import date, timedelta
    import notes as desk_notes
    keep = (desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR, desk_notes.INDEX_DIR)
    desk_notes.RESEARCH_DIR = str(tmp_path / "research")
    desk_notes.NOTES_DIR = str(tmp_path / "research" / "notes")
    desk_notes.FILES_DIR = str(tmp_path / "research" / "files")
    desk_notes.LEGACY_NOTES_DIR = str(tmp_path / "notes")
    desk_notes.INDEX_DIR = str(tmp_path / "research" / "index" / "text")
    try:
        today = date.today()
        t = desk_notes.add_task("check the segment split", "aapl", (today - timedelta(days=3)).isoformat(), "filing", "an answer on Ticker AAPL")
        assert t["symbol"] == "AAPL" and t["line"] == 4
        line = open(tmp_path / "research" / "tasks.md", encoding="utf-8").read().split("\n")[4]
        assert line == f"- [ ] check the segment split · $AAPL · due {(today - timedelta(days=3)).isoformat()} · filing · via an answer on Ticker AAPL"
        assert desk_notes._parse_task_line(4, line)["source"] == "an answer on Ticker AAPL"
        desk_notes.add_task("read the rubber note")
        desk_notes.save({"title": "To-dos", "symbols": ["MSFT"], "body": "- [ ] rebuild the model\n- [x] read the call\n"})
        cal = [{"symbol": "AAPL", "date": (today + timedelta(days=2)).isoformat()},
               {"code": "MSFT", "date": (today + timedelta(days=20)).isoformat()},
               {"symbol": "OLD", "date": (today - timedelta(days=1)).isoformat()}]          # in the past: no task
        v = desk_notes.tasks_view(cal)
        o = v["open"]
        assert [x["text"] for x in o["overdue"]] == ["check the segment split"]
        assert [x["text"] for x in o["week"]] == ["AAPL results"] and o["week"][0]["source"] == "calendar" and o["week"][0]["line"] == -1
        assert [x["text"] for x in o["later"]] == ["MSFT results"]
        assert {x["text"] for x in o["undated"]} == {"read the rubber note", "rebuild the model"}
        assert [x["text"] for x in v["done"]] == ["read the call"] and v["counts"]["due"] == 1
        # ticking: a written task, a checkbox in a note, and a calendar task (written down as done so it stays ticked)
        assert desk_notes.tick_task(4, True)["done_at"] == today.isoformat()
        assert "[x] rebuild the model" in desk_notes.tick_note_task("to-dos", 0, True)["body"]
        ct = desk_notes.add_task("AAPL results", "AAPL", (today + timedelta(days=2)).isoformat(), "results", "calendar")
        desk_notes.tick_task(ct["line"], True)
        v2 = desk_notes.tasks_view(cal)
        assert v2["open"]["week"] == [] and v2["counts"]["open"] == 2 and len(v2["done"]) == 4
        assert desk_notes.tick_task(4, False)["done"] is False and desk_notes.delete_task(4)
        assert desk_notes.tasks_view(cal, symbol="MSFT")["counts"]["open"] == 1                # MSFT results only; the note's checkbox is done
    finally:
        desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.LEGACY_NOTES_DIR, desk_notes.INDEX_DIR = keep
        desk_notes.index(force=True)


def test_live_blocks_resolve(monkeypatch):
    """A fenced desk block resolves to data the page can draw, and a bad block answers with an
    error in place rather than breaking the note: unknown kinds, missing symbols, a commodity
    that is not on the board. Quotes come from the watch pools when they hold the name."""
    import server
    monkeypatch.setitem(server.WATCH_US, "AAPL", {"code": "AAPL", "name": "Apple Inc.", "ltp": 100.0, "prev": 90.0, "day_pct": 11.1, "chg": 10.0, "ts": "10:00"})
    q = server.resolve_block("quote aapl")
    assert q["kind"] == "quote" and q["rows"][0]["symbol"] == "AAPL" and q["rows"][0]["price"] == 100.0
    assert "error" in server.resolve_block("quote") and "error" in server.resolve_block("chart")
    bad = server.resolve_block("nonsense AAPL")
    assert "no block called" in bad["error"] and "chart" in bad["known"]
    c = server.resolve_block("commodity nothing-like-this")
    assert "error" in c
    t = server.resolve_block("tasks")
    assert "tasks" in t and "open" in t["tasks"]
    assert server.resolve_block("")["error"]
    assert set(server.BLOCKS) == {"quote", "chart", "watch", "commodity", "status", "notes", "tasks", "timeline", "book"}


def test_plugins_load_install_remove(tmp_path, monkeypatch):
    """A plugin is a folder with a plugin.json: the loader reads what it adds (a screen, blocks,
    a door), serves only files inside its own folder, brings one in from a zip that cannot
    reach outside, refuses a zip without plugin.json, and removes it in one call. The shipped
    plugins in plugins/ load, and the published list names them."""
    import io
    import json
    import zipfile
    import notes as desk_notes
    import plugins as desk_plugins
    keep = desk_notes.RESEARCH_DIR
    desk_notes.RESEARCH_DIR = str(tmp_path / "research")
    try:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        t = desk_plugins.install_folder(os.path.join(here, "plugins", "terminal"))
        assert t["adds"] == ["a screen", "a door"] and t["door"]["commands"][0]["label"] == "Claude Code"
        h = desk_plugins.install_folder(os.path.join(here, "plugins", "hello"))
        assert h["adds"] == ["a screen", "blocks"] and h["blocks"] == ["/plugins/hello/blocks.js"]
        assert [p["name"] for p in desk_plugins.installed(force=True)] == ["hello", "terminal"]
        assert [s["key"] for s in desk_plugins.screens()] == ["plugin:hello", "plugin:terminal"]
        assert desk_plugins.doors()[0]["name"] == "terminal"
        assert desk_plugins.file_path("hello", "screen.html") and desk_plugins.file_path("hello", "../terminal/plugin.json") is None
        assert desk_plugins.file_path("hello", "plugin.py") is None            # only the kinds a page needs
        # a zip: one top folder, plugin.json inside
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("mine/plugin.json", json.dumps({"name": "mine", "label": "Mine", "screen": {"label": "Mine"}}))
            z.writestr("mine/screen.html", "<p>hi</p>")
        m = desk_plugins.install_zip(buf.getvalue())
        assert m["name"] == "mine" and (tmp_path / "research" / "plugins" / "mine" / "screen.html").read_text() == "<p>hi</p>"
        bad = io.BytesIO()
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("x/../../escape.txt", "no")
            z.writestr("x/plugin.json", "{}")
        try:
            desk_plugins.install_zip(bad.getvalue())
            assert False, "a zip that reaches outside must be refused"
        except ValueError:
            pass
        nometa = io.BytesIO()
        with zipfile.ZipFile(nometa, "w") as z:
            z.writestr("y/readme.md", "no")
        try:
            desk_plugins.install_zip(nometa.getvalue())
            assert False
        except ValueError:
            pass
        try:
            desk_plugins.install_zip(buf.getvalue(), expect_name="other")
            assert False, "the list's name must match the zip's"
        except ValueError:
            pass
        assert desk_plugins.remove("mine") and desk_plugins.remove("mine") is False
        assert [p["name"] for p in desk_plugins.installed(force=True)] == ["hello", "terminal"]
        assert desk_plugins.run_door("nothing", "x")["ok"] is False
        with open(os.path.join(here, "docs", "plugins", "index.json"), encoding="utf-8") as fh:
            lst = json.load(fh)
        assert {p["name"] for p in lst["plugins"]} >= {"terminal", "hello"} and all(p["zip"].startswith("https://greeksoup.ai/plugins/") for p in lst["plugins"])
    finally:
        desk_notes.RESEARCH_DIR = keep
        desk_plugins.installed(force=True)


def test_backup_restore_round_trip(tmp_path, monkeypatch):
    """A backup back in: files under data/ are written; a file that would change is kept aside
    first; the same file is counted, not rewritten; a zip that reaches outside data/ or has
    no data/ is refused."""
    import io
    import zipfile
    import settings as desk_settings
    import notes as desk_notes
    monkeypatch.setattr(desk_settings, "HERE", str(tmp_path))
    keep = desk_notes.RESEARCH_DIR
    desk_notes._point_at(str(tmp_path / "data" / "research"))          # _point_at scans, which makes notes/
    (tmp_path / "data" / "research" / "notes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "book.json").write_text('{"positions": [1]}', encoding="utf-8")
    (tmp_path / "data" / "research" / "notes" / "a.md").write_text("old", encoding="utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("data/book.json", '{"positions": [1]}')                 # the same: untouched
        z.writestr("data/research/notes/a.md", "new")                    # changed: kept aside, then written
        z.writestr("data/research/notes/b.md", "fresh")                  # new: written
        z.writestr("data/.env", "SECRET=1")                              # never restored
        z.writestr("VERSION", "x")                                       # not data/: ignored
    rep = desk_settings.restore_zip(buf.getvalue())
    assert rep["unchanged"] == 1 and sorted(rep["written"]) == ["data/research/notes/a.md", "data/research/notes/b.md"]
    assert rep["kept"] == ["data/research/notes/a.md"] and rep["kept_in"]
    assert (tmp_path / "data" / "research" / "notes" / "a.md").read_text() == "new"
    kept = os.path.join(rep["kept_in"], "data", "research", "notes", "a.md")
    assert open(kept, encoding="utf-8").read() == "old"
    assert not (tmp_path / "data" / ".env").exists() and not (tmp_path / "VERSION").exists()
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("data/../escape.txt", "no")
    for blob in (bad.getvalue(), b"not a zip"):
        try:
            desk_settings.restore_zip(blob)
            assert False, "must be refused"
        except ValueError:
            pass
    nodata = io.BytesIO()
    with zipfile.ZipFile(nodata, "w") as z:
        z.writestr("readme.md", "x")
    try:
        desk_settings.restore_zip(nodata.getvalue())
        assert False
    except ValueError:
        pass
    desk_notes._point_at(keep)


def test_us_panels_live_on_home():
    """Desk · US is no longer a screen of its own: the sidebar list has no usdesk key, nothing is
    hidden by the home market any more, /usdesk lands on Desk · Home, and the Ask box on Home
    reads the US book, the earnings countdown and the insider tape along with the broker book."""
    import server
    assert "usdesk" not in {k for k, _, _ in server.SCREENS}
    nav = server.nav_state()
    assert nav["default_hidden"] == [] and "usdesk" not in nav["hidden"]
    reads = server.ASK_READS["/"][1]
    assert "/api/usbook" in reads and "/api/earnings" in reads and "/api/insiders" in reads
    assert "/usdesk" not in server.ASK_READS
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = open(os.path.join(here, "web", "index.html"), encoding="utf-8").read()
    assert 'id="usdesk"' in home and "usdesk.js" in home and "usdesk.css" in home
    assert not os.path.exists(os.path.join(here, "web", "usdesk.html"))
    js = open(os.path.join(here, "web", "assets", "desk.js"), encoding="utf-8").read()
    assert '"/usdesk"' not in js


def test_vault_relocates_and_adopts(tmp_path):
    """The vault moves to a folder the reader syncs, and comes back: files the target lacks move,
    identical ones are dropped, a differing one stays in the target with the local copy kept
    aside; every path the vault uses follows the new root at once; the desk's own folders are
    refused as a target."""
    import notes as desk_notes
    keep = (desk_notes.RESEARCH_DIR, desk_notes.NOTES_DIR, desk_notes.FILES_DIR, desk_notes.INDEX_DIR, desk_notes.HERE)
    desk_notes.HERE = str(tmp_path / "desk")
    (tmp_path / "desk" / "cache").mkdir(parents=True)
    desk_notes._point_at(str(tmp_path / "desk" / "data" / "research"))
    try:
        desk_notes.save({"title": "Mine", "body": "local"})
        desk_notes.save({"title": "Shared", "body": "local version"})
        desk_notes.set_status("AAPL", "researching")
        synced = tmp_path / "drive" / "vault"
        (synced / "notes").mkdir(parents=True)
        (synced / "notes" / "shared.md").write_text("---\ntitle: Shared\n---\nremote version", encoding="utf-8")
        (synced / "notes" / "theirs.md").write_text("---\ntitle: Theirs\n---\nfrom the other machine", encoding="utf-8")
        rep = desk_notes.relocate(str(synced))
        assert rep["adopted"] and rep["moved"] == 2 and rep["kept"] == ["notes/shared.md"]     # mine.md + status.json moved; shared kept aside
        assert desk_notes.RESEARCH_DIR == str(synced) and desk_notes.NOTES_DIR == str(synced / "notes")
        titles = {n["title"] for n in desk_notes.index(force=True).values()}
        assert titles == {"Mine", "Shared", "Theirs"} and desk_notes.get("shared")["body"].startswith("remote")
        assert open(os.path.join(rep["kept_in"], "notes", "shared.md"), encoding="utf-8").read().endswith("local version\n")
        assert desk_notes.status_all()["AAPL"]["status"] == "researching"                       # status.json travelled
        assert not (tmp_path / "desk" / "data" / "research").exists()
        try:
            desk_notes.relocate(str(tmp_path / "desk" / "cache" / "x"))
            assert False, "the desk's cache is refused"
        except ValueError:
            pass
        back = desk_notes.relocate(str(tmp_path / "desk" / "data" / "research"))
        assert back["moved"] == 4 and desk_notes.vault_location()["path"] == str(tmp_path / "desk" / "data" / "research")
        assert {n["title"] for n in desk_notes.index(force=True).values()} == {"Mine", "Shared", "Theirs"}
    finally:
        desk_notes.HERE = keep[4]
        desk_notes._point_at(keep[0])



def test_chains_are_the_readers_own(tmp_path):
    """The Chain screen: the starters show until the reader puts one away or makes it theirs;
    a reader's chain is a file in the vault; delete keeps a copy and undo brings it back;
    the starters come back on request; the AI draft is parsed from whatever wraps the JSON."""
    import notes as desk_notes
    import chains as desk_chains
    keep = desk_notes.RESEARCH_DIR
    desk_notes._point_at(str(tmp_path / "research"))
    try:
        first = desk_chains.list_all()
        starters = [c for c in first["chains"] if c.get("starter")]
        assert starters and first["hidden_starters"] == 0 and all(not c["own"] for c in starters)
        sid = starters[0]["id"]
        # put a starter away, then bring it back
        assert desk_chains.delete(sid)["kind"] == "starter"
        after = desk_chains.list_all()
        assert sid not in {c["id"] for c in after["chains"]} and after["hidden_starters"] == 1
        desk_chains.show_starters()
        assert sid in {c["id"] for c in desk_chains.list_all()["chains"]}
        # the reader's own chain: a file in the vault, in the desk's shape whatever came in
        c = desk_chains.save({"title": "Lithium to the car", "region": "IN", "layers": [
            {"name": "Mining", "sells": "spodumene", "names": [{"code": "pls", "label": "Pilbara", "region": "global", "status": "nope", "receipt": "whatever"}]},
            "not a layer", {"name": "Cells", "names": [{"label": "A private cell maker"}]}],
            "edges": [{"from": "Pilbara", "to": "A private cell maker", "what": "offtake"}, {"from": "", "to": "x"}]})
        assert c["id"] == "lithium-to-the-car" and c["region"] == "home" and c["format"] == desk_chains.FORMAT
        assert (tmp_path / "research" / "chains" / "lithium-to-the-car.json").exists()
        assert [l["name"] for l in c["layers"]] == ["Mining", "Cells"] and c["layers"][0]["n"] == 1 and c["layers"][1]["n"] == 2
        nm = c["layers"][0]["names"][0]
        assert nm["code"] == "PLS" and nm["region"] == "global" and nm["status"] == "CONTEXT" and nm["receipt"] == "REPORTED"
        assert c["layers"][1]["names"][0]["code"] == "" and len(c["edges"]) == 1
        rows = desk_chains.list_all()["chains"]
        assert rows[0]["id"] == "lithium-to-the-car" and rows[0]["own"]                     # the reader's own first
        # making a starter theirs: the copy is the reader's, the starter steps aside
        mine = dict(starters[0]); mine["title"] = "My " + mine["title"]
        desk_chains.save(mine)
        rows = desk_chains.list_all()["chains"]
        assert [r for r in rows if r["id"] == sid][0]["own"] and not any(r.get("starter") and r["id"] == sid for r in rows)
        # delete keeps a copy; undo brings it back
        out = desk_chains.delete("lithium-to-the-car")
        assert out["kind"] == "own" and not (tmp_path / "research" / "chains" / "lithium-to-the-car.json").exists()
        assert "lithium-to-the-car" not in {r["id"] for r in desk_chains.list_all()["chains"]}
        assert desk_chains.undo_delete(out["undo"])["ok"] and (tmp_path / "research" / "chains" / "lithium-to-the-car.json").exists()
        assert not desk_chains.undo_delete("../../etc/passwd")["ok"]
        try:
            desk_chains.save({"title": "Empty"})
            assert False, "a chain needs a layer"
        except ValueError:
            pass
        # the draft: JSON out of prose or a fence, held and watched names marked, nothing saved
        reply = 'Here you go:\n```json\n{"title":"Copper","region":"us","layers":[{"name":"Mines","names":[{"code":"FCX","label":"Freeport","status":"OWNED","receipt":"DISCLOSED","source":"10-K"}]}],"edges":[]}\n```'
        seen = {}
        d = desk_chains.draft("the copper chain from mine to wire", "US", held={"FCX"}, watched=set(),
                              ask=lambda messages, system: seen.update(m=messages, s=system) or {"ok": True, "text": reply})
        assert d["ok"] and d["chain"]["title"] == "Copper" and d["chain"]["layers"][0]["names"][0]["status"] == "OWNED"
        assert "FCX" in seen["m"][0]["content"] and "DISCLOSED only when" in seen["s"]
        assert not (tmp_path / "research" / "chains" / "copper.json").exists()
        bad = desk_chains.draft("the copper chain from mine to wire", "US", ask=lambda m, s: {"ok": True, "text": "no map today"})
        assert not bad["ok"] and "shape" in bad["error"]
        assert not desk_chains.draft("hi", "US", ask=lambda m, s: {"ok": True, "text": ""})["ok"]
    finally:
        desk_notes._point_at(keep)
