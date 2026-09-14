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


def test_docs_nav_points_at_real_pages():
    nav = json.load(open(os.path.join(HERE, "site", "nav.json"), encoding="utf-8"))
    for sec in nav["sections"]:
        for page in sec["pages"]:
            path = os.path.join(HERE, "site", sec["dir"], page + ".md")
            assert os.path.isfile(path), f"docs page missing: {path}"
