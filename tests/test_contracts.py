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
