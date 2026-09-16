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


def _read(name, folder=None):
    folder = folder or os.path.join(plugins_dir(), name)
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
                build = c.get("build") if isinstance(c.get("build"), list) and all(isinstance(x, str) for x in c.get("build")) else []
                # "web": the flags that let the app search the web (an empty list: it searches
                # without a flag); no key at all: the desk does not know how, so the box greys it
                web = c.get("web") if isinstance(c.get("web"), list) and all(isinstance(x, str) for x in c.get("web")) else None
                cmds.append({"label": str(c.get("label") or c["command"][0])[:40], "command": c["command"][:12], "found": bool(found), "path": found or "",
                             "prompt": "arg" if c.get("prompt") == "arg" else "stdin", "build": build[:6],
                             "web": web[:6] if web is not None else None})
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
            # the Terminal door ships with the desk: every reader can hand a question to
            # an app they already pay for without installing anything; a copy the reader
            # brought into the vault (to edit) takes the shipped one's place
            if not any(p["name"] == "terminal" for p in rows) and os.path.isdir(os.path.join(SHIPPED_DIR, "terminal")):
                rows.append(_read("terminal", os.path.join(SHIPPED_DIR, "terminal")) | {"builtin": True})
            _cache["rows"], _cache["at"] = rows, time.time()
        return list(_cache["rows"])


def screens():
    return [p["screen"] for p in installed() if p.get("screen")]


def block_files():
    return [f for p in installed() for f in p.get("blocks", [])]


# the apps a door can be: the reader's own subscription, through the app's own login; the desk
# never sees the token, it hands the app a question and reads the answer
APPS = {
    # The apps the desk knows how to hand a question to. Each one is the maker's own command-line
    # app, run as the reader would run it; the desk never sees the login. `signin` is what a
    # terminal window runs so the reader can sign in inside the app itself.
    # `model_flag` is the app's own switch for picking a model; `models` the names the desk
    # offers in the Ask box (the app's default always comes first, and any name the reader
    # types is passed through as typed). An app without a flag picks its own model.
    "claude": {"label": "Claude Code", "pays": "your Claude subscription", "site": "https://claude.com/product/claude-code",
               "signin": "claude", "model_flag": "--model",
               "models": [["claude-opus-5", "Opus 5"], ["claude-fable-5-1", "Fable 5.1"], ["claude-fable-5", "Fable 5"],
                          ["claude-opus-4-8", "Opus 4.8"], ["claude-opus-4-7", "Opus 4.7"], ["claude-opus-4-6", "Opus 4.6"],
                          ["claude-sonnet-5", "Sonnet 5"], ["claude-sonnet-4-6", "Sonnet 4.6"], ["claude-haiku-4-5", "Haiku 4.5"]]},
    "codex": {"label": "Codex", "pays": "your ChatGPT subscription", "site": "https://openai.com/codex/", "signin": "codex login",
              "model_flag": "-m", "models": []},
    "gemini": {"label": "Gemini CLI", "pays": "your Google account", "site": "https://github.com/google-gemini/gemini-cli", "signin": "gemini",
               "model_flag": "-m", "models": []},
    "kimi": {"label": "Kimi Code", "pays": "your Kimi account", "site": "https://www.kimi.com/code", "signin": "kimi"},
    "grok": {"label": "Grok Build", "pays": "your xAI account", "site": "https://x.ai/build", "signin": "grok",
             "model_flag": "-m", "models": []},
    "qwen": {"label": "Qwen Code", "pays": "your Qwen account", "site": "https://qwen.ai/qwencode", "signin": "qwen",
             "model_flag": "-m", "models": []},
    "cursor-agent": {"label": "Cursor", "pays": "your Cursor subscription", "site": "https://cursor.com/docs/cli/overview",
                     "signin": "cursor-agent login", "model_flag": "--model", "models": []},
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
                        "ready": bool(c["found"]), "via": c["label"], "app": os.path.basename(c["command"][0]),
                        "build": bool(c.get("build")), "web": c.get("web") is not None, "model_flag": app.get("model_flag", ""),
                        "models": app.get("models", [])})
    return out


# how the desk asks an app whether it is signed in: the app's own status command where it
# has one (cheap, no model call); otherwise one tiny question through the door
STATUS_CMD = {
    "claude": ["auth", "status"],
    "codex": ["login", "status"],
    "cursor-agent": ["status"],
}


def signed_in(app):
    """{"state": "in" | "out" | "unknown", "text": the app's own words}. Reads the app's status
    command when it has one; an app without one is asked a one-word question through its door,
    which is the only way to know its login holds."""
    a = APPS.get(app)
    path = _which(app) if a else None
    if not a or not path:
        return {"state": "unknown", "text": "not on this computer"}
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)
    if app in STATUS_CMD:
        try:
            r = subprocess.run([path] + STATUS_CMD[app], capture_output=True, text=True, timeout=20, env=env)
        except (subprocess.TimeoutExpired, OSError) as exc:
            return {"state": "unknown", "text": f"the status command did not answer ({type(exc).__name__})"}
        text = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
        low = text.lower()
        if app == "claude":
            try:
                j = json.loads(r.stdout or "{}")
                ok, how = bool(j.get("loggedIn")), str(j.get("authMethod") or "")
            except ValueError:
                ok, how = "loggedin\": true" in low.replace(" ", ""), ""
            return {"state": "in" if ok else "out", "text": (f"through {how}" if ok and how else "")}
        if "not logged in" in low or "not signed in" in low or "no credentials" in low or "unauthenticated" in low:
            return {"state": "out", "text": text.splitlines()[0][:160] if text else "not signed in"}
        if r.returncode == 0 and ("logged in" in low or "signed in" in low or "authenticated" in low or "@" in low):
            return {"state": "in", "text": text.splitlines()[0][:160] if text else "signed in"}
        return {"state": "unknown", "text": (text.splitlines()[0][:160] if text else f"exit {r.returncode}")}
    door = next((d["name"] for d in doors() if d["app"] == app and d["ready"]), "")
    if not door:
        return {"state": "unknown", "text": "no door reaches it yet; the Terminal door plugin brings one"}
    out = run_door(door, "Reply with the single word: ok", timeout=90)
    if out.get("ok"):
        return {"state": "in", "text": "signed in; it answered"}
    return {"state": "out", "text": (out.get("error") or "it did not answer")[:200]}


def apps_known():
    """Every app the desk knows how to talk to, found on this computer or not, for the Your AI
    card. Found is read from the computer itself, so it is right before any door plugin is in;
    `door` names the door that reaches it once the Terminal plugin is installed."""
    seen = {d["app"]: d for d in doors()}
    rows = []
    for key, a in APPS.items():
        d = seen.get(key)
        rows.append({"app": key, "label": a["label"], "pays": a["pays"], "site": a["site"], "signin": a["signin"],
                     "found": bool(_which(key)), "door": d["name"] if d else "", "installed": bool(d),
                     "cheap_check": key in STATUS_CMD})
    return rows


SHIPPED_DIR = os.path.join(HERE, "plugins")


def refresh_shipped():
    """A plugin that ships beside the code (the Terminal door, the example) and is installed in
    the vault is brought up to the shipped version when a release carries a newer one; the
    reader did not write it, so nothing of theirs is touched. Returns the names refreshed."""
    done = []
    for p in installed():
        src = os.path.join(SHIPPED_DIR, p["name"])
        if not os.path.isfile(os.path.join(src, "plugin.json")):
            continue
        try:
            with open(os.path.join(src, "plugin.json"), encoding="utf-8") as fh:
                shipped = json.load(fh)
            if str(shipped.get("author", "")) != "Shikshan Nivesh" or str(p.get("author", "")) != "Shikshan Nivesh":
                continue
            if int(str(shipped.get("version", "0")) or 0) > int(str(p.get("version", "0")) or 0):
                install_folder(src)
                done.append(p["name"])
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return done


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


# the door runs in flight, by the Ask box's own id, so a Stop press can end it
_running = {}
_stopped = set()


def stop_door(ask_id):
    """End the app run the Ask box started under this id, if it is still going."""
    ask_id = str(ask_id or "")
    proc = _running.get(ask_id)
    if not proc:
        return False
    _stopped.add(ask_id)
    try:
        proc.terminate()
    except OSError:
        return False
    return True


def run_door(name, prompt, timeout=240, mode="research", model="", ask_id=""):
    """Hand the Ask box's prompt to the door's command on this computer and return what it
    says. The command is the plugin's own, found on PATH; nothing else is run. In Build mode
    the app runs in the desk's own folder with the edit flags its plugin.json names, so it
    can change the desk as the reader asked; an app whose command has no build flags stays
    research-only."""
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
    if mode == "build":
        if not ready.get("build"):
            return {"ok": False, "error": f"{ready['label']} answers questions here but the desk does not know how to let it edit files yet; pick Claude Code, Codex, Gemini CLI or Qwen Code for Build, or ask on Settings for it to be added."}
        cmd = [cmd[0]] + list(ready["build"]) + cmd[1:]
    elif mode == "web":
        if ready.get("web") is None:
            return {"ok": False, "error": f"The desk does not know how to let {ready['label']} search the web; Claude Code, Codex and Gemini CLI can. Or pick Research, which reads the desk alone."}
        cmd = [cmd[0]] + list(ready["web"]) + cmd[1:]
    # Most apps read the question on standard input; an app whose command says
    # "prompt": "arg" takes it as its last argument instead (Kimi Code has no stdin mode).
    as_arg = ready.get("prompt") == "arg"
    # the model the reader picked in the Ask box, through the app's own switch; an app
    # without one picks its own model and the box says so
    app = APPS.get(os.path.basename(ready["command"][0]), {})
    model = re.sub(r"[^A-Za-z0-9._:/-]", "", str(model or ""))[:80]
    if model and app.get("model_flag"):
        cmd = [cmd[0], app["model_flag"], model] + cmd[1:]
    if as_arg:
        cmd.append(prompt)
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)                       # a nested session refuses to start
    ask_id = str(ask_id or "")
    try:
        cwd = HERE if mode == "build" else (desk_notes.RESEARCH_DIR if os.path.isdir(desk_notes.RESEARCH_DIR) else HERE)
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=cwd)
        if ask_id:
            _running[ask_id] = proc
        try:
            out, err = proc.communicate("" if as_arg else prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return {"ok": False, "error": f"{ready['label']} did not answer within {timeout // 60} minutes"}
        finally:
            _running.pop(ask_id, None)
    except OSError as exc:
        return {"ok": False, "error": f"{ready['label']} could not be started ({exc})"}
    text = (out or "").strip()
    if ask_id in _stopped:
        _stopped.discard(ask_id)
        return {"ok": False, "error": "Stopped.", "stopped": True}
    if proc.returncode != 0 and not text:
        return {"ok": False, "error": f"{ready['label']} returned an error: " + ((err or "").strip()[-400:] or f"exit {proc.returncode}")}
    label = ready["label"] + (f" · {model}" if model else "")
    return {"ok": True, "answer": text or "(the agent sent an empty answer)", "via": label}
