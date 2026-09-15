"""Plugins: folders the reader drops into data/research/plugins/, each with a plugin.json
that says what it adds and the files that add it. Three kinds, each small:

  a screen   a page in the sidebar, an HTML file that reads the desk's own JSON addresses
  blocks     a JavaScript file that registers renderers with window.deskBlocks.register
  a door     a way to talk: a command on this computer that takes the Ask box's prompt on
             standard input and answers on standard output (the terminal door: the coding
             agent the reader already has)

    data/research/plugins/terminal/
      plugin.json
      {
        "name": "terminal", "label": "Terminal door", "version": "1",
        "what": "Answers the Ask box through the coding agent installed on this computer.",
        "talks_to": ["the coding agent on this computer (Claude Code or Codex); it may reach its own provider"],
        "door": {"label": "Terminal", "commands": [
            {"label": "Claude Code", "command": ["claude", "-p", "--output-format", "text"]},
            {"label": "Codex", "command": ["codex", "exec", "-"]}]},
        "screen": {"href": "/plugins/terminal/screen.html", "label": "Terminal", "group": "Plugins"},
        "blocks": ["blocks.js"]
      }

A plugin runs on the reader's computer and reads what the reader lets it; the desk shows
what each one adds and what it talks to before it goes in, and removes it in one click.
The public list (step 8) is a JSON file the desk's Settings reads: name, what it adds, who
wrote it, a zip to bring in. Nothing here is installed on its own.
"""
import io
import json
import os
import re
import shutil
import subprocess
import threading
import time
import zipfile

import notes as desk_notes

HERE = os.path.dirname(os.path.abspath(__file__))
SERVE_EXT = {".html", ".js", ".css", ".json", ".png", ".svg", ".jpg", ".jpeg", ".webp", ".md", ".txt"}
ZIP_CAP = 20 * 1024 * 1024
_lock = threading.Lock()
_cache = {"at": 0.0, "rows": None}


def plugins_dir():
    return os.path.join(desk_notes.RESEARCH_DIR, "plugins")


def _which(name):
    """Find a command the way a terminal would, even though the desk runs as a service with a
    bare PATH: the PATH it has, then the folders where coding agents get installed."""
    if os.path.isabs(name):
        return name if os.path.isfile(name) and os.access(name, os.X_OK) else None
    hit = shutil.which(name)
    if hit:
        return hit
    home = os.path.expanduser("~")
    extra = [os.path.join(home, ".local", "bin"), os.path.join(home, ".npm-global", "bin"), os.path.join(home, ".bun", "bin"),
             os.path.join(home, ".cargo", "bin"), os.path.join(home, "bin"), "/usr/local/bin", "/opt/homebrew/bin", "/usr/bin",
             os.path.join(home, ".volta", "bin"), os.path.join(home, ".nvm", "current", "bin"), os.path.join(home, "node_modules", ".bin")]
    if os.name == "nt":
        extra += [os.path.join(os.getenv("APPDATA", ""), "npm"), os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", name),
                  os.path.join(os.getenv("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links")]
    nvm = os.path.join(home, ".nvm", "versions", "node")
    if os.path.isdir(nvm):
        for v in sorted(os.listdir(nvm), reverse=True)[:3]:
            extra.append(os.path.join(nvm, v, "bin"))
    return shutil.which(name, path=os.pathsep.join(p for p in extra if p))


def _safe_name(name):
    return re.sub(r"[^a-z0-9-]", "", (name or "").lower())[:40]


def _read(name):
    folder = os.path.join(plugins_dir(), name)
    try:
        with open(os.path.join(folder, "plugin.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, ValueError) as exc:
        return {"name": name, "error": f"plugin.json could not be read ({type(exc).__name__})", "folder": folder}
    if not isinstance(meta, dict):
        return {"name": name, "error": "plugin.json is not an object", "folder": folder}
    out = {"name": name, "label": str(meta.get("label") or name)[:60], "version": str(meta.get("version") or "")[:20],
           "what": str(meta.get("what") or "")[:300], "author": str(meta.get("author") or "")[:80],
           "talks_to": [str(x)[:120] for x in (meta.get("talks_to") or [])][:8], "folder": folder, "adds": []}
    scr = meta.get("screen")
    if isinstance(scr, dict) and scr.get("label"):
        href = str(scr.get("href") or f"/plugins/{name}/screen.html")
        if not href.startswith(f"/plugins/{name}/"):
            href = f"/plugins/{name}/screen.html"
        out["screen"] = {"href": href, "label": str(scr["label"])[:30], "group": str(scr.get("group") or "Plugins")[:30], "key": "plugin:" + name}
        out["adds"].append("a screen")
    blocks = [b for b in (meta.get("blocks") or []) if isinstance(b, str) and b.endswith(".js") and "/" not in b and ".." not in b]
    if blocks:
        out["blocks"] = [f"/plugins/{name}/{b}" for b in blocks]
        out["adds"].append("blocks")
    door = meta.get("door")
    if isinstance(door, dict):
        cmds = []
        for c in door.get("commands") or []:
            if isinstance(c, dict) and isinstance(c.get("command"), list) and c["command"] and all(isinstance(x, str) for x in c["command"]):
                found = _which(c["command"][0])
                cmds.append({"label": str(c.get("label") or c["command"][0])[:40], "command": c["command"][:12], "found": bool(found), "path": found or ""})
        out["door"] = {"label": str(door.get("label") or out["label"])[:40], "commands": cmds,
                       "ready": next((c for c in cmds if c["found"]), None)}
        out["adds"].append("a door")
    return out


def installed(force=False):
    """Every plugin in the folder, read at most once every few seconds."""
    with _lock:
        if force or _cache["rows"] is None or time.time() - _cache["at"] > 5:
            rows = []
            d = plugins_dir()
            if os.path.isdir(d):
                for name in sorted(os.listdir(d)):
                    if _safe_name(name) == name and os.path.isdir(os.path.join(d, name)):
                        rows.append(_read(name))
            _cache["rows"], _cache["at"] = rows, time.time()
        return list(_cache["rows"])


def screens():
    return [p["screen"] for p in installed() if p.get("screen")]


def block_files():
    return [f for p in installed() for f in p.get("blocks", [])]


# the apps a door can be: the reader's own subscription, through the app's own login; the desk
# never sees the token, it hands the app a question and reads the answer
APPS = {
    "claude": {"label": "Claude Code", "pays": "your Claude subscription", "site": "https://claude.com/product/claude-code",
               "signin": "claude"},
    "codex": {"label": "Codex", "pays": "your ChatGPT subscription", "site": "https://openai.com/codex/", "signin": "codex login"},
    "gemini": {"label": "Gemini CLI", "pays": "your Google account", "site": "https://github.com/google-gemini/gemini-cli", "signin": "gemini"},
}


def doors():
    """One door per app found on this computer (name plugin:index), so the reader picks the app,
    not the plugin; the bare plugin name still means its first app found."""
    out = []
    for p in installed():
        if not p.get("door"):
            continue
        for i, c in enumerate(p["door"]["commands"]):
            app = APPS.get(os.path.basename(c["command"][0]), {})
            out.append({"name": f"{p['name']}:{i}", "plugin": p["name"], "label": app.get("label") or c["label"],
                        "pays": app.get("pays", ""), "site": app.get("site", ""), "signin": app.get("signin", ""),
                        "ready": bool(c["found"]), "via": c["label"], "app": os.path.basename(c["command"][0])})
    return out


def apps_known():
    """Every app the desk knows how to talk to, found on this computer or not, for the Your AI
    card. Found is read from the computer itself, so it is right before any door plugin is in;
    `door` names the door that reaches it once the Terminal plugin is installed."""
    seen = {d["app"]: d for d in doors()}
    rows = []
    for key, a in APPS.items():
        d = seen.get(key)
        rows.append({"app": key, "label": a["label"], "pays": a["pays"], "site": a["site"], "signin": a["signin"],
                     "found": bool(_which(key)), "door": d["name"] if d else "", "installed": bool(d)})
    return rows


SHIPPED_DIR = os.path.join(HERE, "plugins")


def install_shipped(name):
    """Bring a plugin that ships beside the code into the vault (the Terminal door, when the
    reader picks an app before installing it by hand). Returns the plugin as installed."""
    src = os.path.join(SHIPPED_DIR, _safe_name(name))
    if not os.path.isfile(os.path.join(src, "plugin.json")):
        raise ValueError("no such shipped plugin")
    return install_folder(src)


def file_path(name, rel):
    """A file inside one plugin's folder, or None: never outside it, only the kinds a page needs."""
    name = _safe_name(name)
    rel = (rel or "").replace("\\", "/").strip("/")
    if not name or not rel or ".." in rel.split("/") or os.path.splitext(rel)[1].lower() not in SERVE_EXT:
        return None
    base = os.path.abspath(os.path.join(plugins_dir(), name))
    full = os.path.abspath(os.path.join(base, *rel.split("/")))
    if not full.startswith(base + os.sep) or not os.path.isfile(full):
        return None
    return full


def install_zip(data, expect_name=""):
    """Bring a plugin in from a zip: one top folder (or plugin.json at the root), written under
    plugins/<name>/ after the zip is checked for paths that would leave the folder."""
    if not data or len(data) > ZIP_CAP:
        raise ValueError("the zip is empty or larger than the desk takes (20 MB)")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("that is not a zip file")
    names = [n for n in z.namelist() if not n.endswith("/")]
    if any(n.startswith("/") or ".." in n.split("/") for n in names):
        raise ValueError("the zip reaches outside its folder; refused")
    meta_path = next((n for n in names if n == "plugin.json" or n.endswith("/plugin.json") and n.count("/") == 1), None)
    if not meta_path:
        raise ValueError("no plugin.json at the top of the zip")
    prefix = meta_path[:-len("plugin.json")]
    try:
        meta = json.loads(z.read(meta_path).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ValueError("plugin.json is not valid JSON")
    name = _safe_name(meta.get("name") or prefix.strip("/"))
    if not name:
        raise ValueError("plugin.json needs a name (letters, digits, dashes)")
    if expect_name and name != _safe_name(expect_name):
        raise ValueError(f"the zip holds {name!r}, the list said {expect_name!r}")
    folder = os.path.join(plugins_dir(), name)
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)
    for n in names:
        if not n.startswith(prefix):
            continue
        rel = n[len(prefix):]
        if not rel:
            continue
        dst = os.path.join(folder, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(z.read(n))
    installed(force=True)
    return _read(name)


def install_folder(src):
    """Bring a plugin in from a folder on this computer (copied, the original untouched)."""
    src = os.path.abspath(os.path.expanduser(src or ""))
    if not os.path.isfile(os.path.join(src, "plugin.json")):
        raise ValueError("that folder has no plugin.json")
    with open(os.path.join(src, "plugin.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    name = _safe_name(meta.get("name") or os.path.basename(src))
    if not name:
        raise ValueError("plugin.json needs a name")
    folder = os.path.join(plugins_dir(), name)
    if os.path.abspath(src) == os.path.abspath(folder):
        return _read(name)
    if os.path.exists(folder):
        shutil.rmtree(folder)
    shutil.copytree(src, folder, ignore=shutil.ignore_patterns(".git", "__pycache__", ".DS_Store"))
    installed(force=True)
    return _read(name)


def remove(name):
    name = _safe_name(name)
    folder = os.path.join(plugins_dir(), name)
    if not name or not os.path.isdir(folder):
        return False
    shutil.rmtree(folder)
    installed(force=True)
    return True


def run_door(name, prompt, timeout=240):
    """Hand the Ask box's prompt to the door's command on this computer and return what it
    says. The command is the plugin's own, found on PATH; nothing else is run."""
    pname, _, idx = str(name or "").partition(":")
    p = next((p for p in installed() if p["name"] == _safe_name(pname) and p.get("door")), None)
    if not p:
        return {"ok": False, "error": "no such door"}
    ready = p["door"]["ready"]
    if idx:
        if not idx.isdigit() or int(idx) >= len(p["door"]["commands"]):
            return {"ok": False, "error": "no such door"}
        c = p["door"]["commands"][int(idx)]
        if not c["found"]:
            return {"ok": False, "error": f"{c['label']} is not installed on this computer, or not on the path the desk sees"}
        ready = c
    if not ready:
        want = ", ".join(c["label"] for c in p["door"]["commands"]) or "a command"
        return {"ok": False, "error": f"{p['door']['label']}: none of {want} is installed on this computer, or not on the path the desk sees"}
    cmd = list(ready["command"])
    cmd[0] = ready["path"]
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)                       # a nested session refuses to start
    try:
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, env=env,
                           cwd=desk_notes.RESEARCH_DIR if os.path.isdir(desk_notes.RESEARCH_DIR) else HERE)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"{ready['label']} did not answer within {timeout // 60} minutes"}
    except OSError as exc:
        return {"ok": False, "error": f"{ready['label']} could not be started ({exc})"}
    text = (r.stdout or "").strip()
    if r.returncode != 0 and not text:
        return {"ok": False, "error": f"{ready['label']} returned an error: " + ((r.stderr or "").strip()[-400:] or f"exit {r.returncode}")}
    return {"ok": True, "answer": text or "(the agent sent an empty answer)", "via": ready["label"]}
