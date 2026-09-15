"""The desk updates itself.

Once a day the desk reads the VERSION file on GitHub (no key, one small
request). When a newer version exists, every page shows a banner with the
date and what changed, and one button, "Update the desk". The update:

  1. downloads the repository as a ZIP from GitHub and unpacks it in a
     temporary folder;
  2. reads the new MANIFEST.json, which carries the sha256 of every shipped
     file in this version AND every hash each file has ever shipped with;
  3. copies program files and pages over, EXCEPT a file whose local content
     matches no shipped version: that file was changed on this computer (a
     rewritten broker adapter, a page the reader's agent edited), so it is
     kept as it is and listed in the banner for the agent to merge;
  4. never touches .env, cache/, logs/, the daily tokens, or the reader's
     lists in data/. It adds a data file the reader lacks, merges new alert
     rules into data/alerts.json, and refreshes the desk's own shipped
     reference tables (the commodity board and the US names under it) only
     when the reader has never edited them;
  5. installs any new dependency, then restarts the desk in place.

DESK_AUTO_UPDATE=on in .env applies a newer version without the click.
Nothing here places orders or reads the broker; it reads GitHub and writes
files inside this folder.
"""

import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from datetime import datetime

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "shubhamsborkar/greeksoup"
CACHE_DIR = os.path.join(HERE, "cache")
CHECK_PATH = os.path.join(CACHE_DIR, "update_check.json")
RESULT_PATH = os.path.join(CACHE_DIR, "update_result.json")
CHECK_EVERY = 24 * 3600          # one look at GitHub a day
RESULT_SHOWN_FOR = 3 * 24 * 3600  # the "updated" banner is offered for three days

# Never written by an update, whatever the ZIP contains.
NEVER_TOUCH = (".env", "cache", "logs", "output", ".venv", "venv", ".git",
               "__pycache__", "session_token", ".playwright-cli")
# The desk's own reference tables under data/: refreshed only when the local
# copy is byte-identical to a version that shipped (the reader never edited it).
SHIPPED_DATA = {"commodities.json", "exposure_us.json", "exposure_example.json"}

_lock = threading.Lock()
_state = {"busy": False}
BOOT = time.time()   # when this process started; changes on every restart


# ---------------------------------------------------------------- hashing
def bytes_hash(b):
    """sha256 of content with Windows line endings folded, so a git checkout
    on Windows hashes the same as the ZIP."""
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def file_hash(path):
    try:
        with open(path, "rb") as fh:
            return bytes_hash(fh.read())
    except OSError:
        return None


# ---------------------------------------------------------------- version
def parse_version_text(text):
    """VERSION: one release per line, newest first: `2026-09-13  what changed`."""
    out = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        out.append({"version": parts[0], "notes": parts[1].strip() if len(parts) > 1 else ""})
    return out


def local_releases():
    try:
        with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as fh:
            return parse_version_text(fh.read())
    except OSError:
        return []


def local_version():
    rel = local_releases()
    return rel[0]["version"] if rel else ""


def _urls():
    ver = os.getenv("DESK_UPDATE_VERSION_URL", "").strip() or \
        f"https://raw.githubusercontent.com/{REPO}/main/VERSION"
    zip_ = os.getenv("DESK_UPDATE_ZIP_URL", "").strip() or \
        f"https://codeload.github.com/{REPO}/zip/refs/heads/main"
    return ver, zip_


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    os.replace(tmp, path)


def check(force=False):
    """What GitHub says today. Cached for a day; `force` asks again now."""
    cached = _read_json(CHECK_PATH)
    if cached and not force and time.time() - cached.get("at", 0) < CHECK_EVERY:
        cached["local"] = local_version()
        cached["available"] = bool(cached.get("remote")) and cached["remote"] > cached["local"]
        return cached
    ver_url, _ = _urls()
    local = local_version()
    out = {"at": time.time(), "checked": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "local": local, "remote": None, "notes": [], "available": False, "error": None}
    try:
        r = requests.get(ver_url, timeout=12, headers={"User-Agent": "research-desk update check"})
        r.raise_for_status()
        rel = parse_version_text(r.text)
        if not rel:
            raise ValueError("VERSION file on GitHub is empty")
        out["remote"] = rel[0]["version"]
        out["notes"] = [x for x in rel if x["version"] > local][:4]
        out["available"] = out["remote"] > local
    except Exception as exc:  # noqa: BLE001 - offline is normal; keep the last answer
        out["error"] = str(exc)[:200]
        if cached:
            cached["error"] = out["error"]
            cached["local"] = local
            return cached
    try:
        _write_json(CHECK_PATH, out)
    except OSError:
        pass
    return out


def last_result():
    res = _read_json(RESULT_PATH)
    if res and time.time() - res.get("at", 0) < RESULT_SHOWN_FOR:
        return res
    return None


def status(force=False):
    return {"check": check(force), "last_result": last_result(),
            "busy": _state["busy"], "auto": auto_enabled(),
            "local": local_version(), "started": BOOT}


def auto_enabled():
    return os.getenv("DESK_AUTO_UPDATE", "").strip().lower() in ("on", "1", "true", "yes")


# ---------------------------------------------------------------- the update
def _safe_extract(zf, dest):
    dest = os.path.abspath(dest)
    for m in zf.infolist():
        target = os.path.abspath(os.path.join(dest, m.filename))
        if not target.startswith(dest + os.sep):
            raise ValueError("zip entry outside the folder: " + m.filename)
    zf.extractall(dest)


def _download(tmp):
    _, zip_url = _urls()
    r = requests.get(zip_url, timeout=120, headers={"User-Agent": "research-desk update"})
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        _safe_extract(zf, tmp)
    roots = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
    if len(roots) != 1:
        raise ValueError("unexpected ZIP layout")
    return os.path.join(tmp, roots[0])


def _rule_signature(rule):
    """Two alert rules are 'the same rule' when their identifying fields match;
    a threshold the reader changed does not make it a new rule."""
    t = rule.get("type", "")
    keys = {"commodity_move": ("window",), "day_move": ("scope",),
            "price_level": ("symbol", "region")}.get(t, ())
    return (t,) + tuple(str(rule.get(k, "")) for k in keys)


def _merge_alerts(new_path, local_path):
    new = _read_json(new_path) or {}
    loc = _read_json(local_path)
    if loc is None:
        shutil.copy2(new_path, local_path)
        return len(new.get("rules", []))
    have = {_rule_signature(r) for r in loc.get("rules", [])}
    added = [r for r in new.get("rules", []) if _rule_signature(r) not in have]
    if added:
        loc.setdefault("rules", []).extend(added)
        if "_comment" in new:
            loc["_comment"] = new["_comment"]
        _write_json(local_path, loc)
    return len(added)


def _copy_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    mode = None
    try:
        mode = stat.S_IMODE(os.stat(dst).st_mode)
    except OSError:
        pass
    tmp = dst + ".updating"
    shutil.copyfile(src, tmp)
    if mode is None and dst.endswith((".command", ".sh")):
        mode = 0o755
    if mode is not None:
        os.chmod(tmp, mode)
    os.replace(tmp, dst)


def _untouchable(rel):
    top = rel.split("/", 1)[0]
    return top in NEVER_TOUCH or rel.startswith("session_token") or top.startswith(".env")


PREVIOUS = os.path.join(HERE, "cache", "previous")


def _keep_old(dst, rel, snap):
    """Before a file is replaced, its current copy goes into cache/previous/<version>/,
    so the reader can go back if the newer version misbehaves."""
    if not os.path.isfile(dst):
        return
    keep = os.path.join(snap, *rel.split("/"))
    os.makedirs(os.path.dirname(keep), exist_ok=True)
    shutil.copy2(dst, keep)


def previous_versions():
    """The versions a rollback can go back to, newest first."""
    try:
        names = [n for n in os.listdir(PREVIOUS) if os.path.isdir(os.path.join(PREVIOUS, n))]
    except OSError:
        return []
    names.sort(key=lambda n: os.path.getmtime(os.path.join(PREVIOUS, n)), reverse=True)
    return names


def rollback(version=None):
    """Put back the files the last update replaced (or the update to `version`).
    Touches only the files that were kept, never .env, data or cache."""
    names = previous_versions()
    if not names:
        return {"ok": False, "error": "no previous version is kept on this computer"}
    version = version or names[0]
    snap = os.path.join(PREVIOUS, version)
    if not os.path.isdir(snap):
        return {"ok": False, "error": f"no kept copy of {version}"}
    rep = {"ok": False, "to": version, "restored": 0, "error": None, "at": time.time()}
    try:
        for dp, _, files in os.walk(snap):
            for f in files:
                src = os.path.join(dp, f)
                rel = os.path.relpath(src, snap)
                if _untouchable(rel.replace(os.sep, "/")):
                    continue
                _copy_file(src, os.path.join(HERE, rel))
                rep["restored"] += 1
        shutil.rmtree(snap, ignore_errors=True)
        rep["ok"] = True
        try:
            os.remove(CHECK_PATH)
        except OSError:
            pass
    except Exception as exc:  # noqa: BLE001
        rep["error"] = str(exc)[:300]
    try:
        _write_json(RESULT_PATH, rep)
    except OSError:
        pass
    return rep


def apply():
    """Bring the newer version in. Returns a plain report; the caller restarts."""
    with _lock:
        if _state["busy"]:
            return {"ok": False, "error": "an update is already running"}
        _state["busy"] = True
    tmp = tempfile.mkdtemp(prefix="desk-update-")
    started = time.time()
    rep = {"ok": False, "from": local_version(), "to": None, "copied": 0, "unchanged": 0,
           "kept": [], "added_data": [], "refreshed_data": [], "added_rules": 0,
           "pip": "skipped", "error": None, "at": time.time()}
    try:
        root = _download(tmp)
        manifest = _read_json(os.path.join(root, "MANIFEST.json"))
        if not manifest or "files" not in manifest:
            raise ValueError("the new version carries no MANIFEST.json")
        rep["to"] = manifest.get("version") or (parse_version_text(
            open(os.path.join(root, "VERSION"), encoding="utf-8").read()) or [{}])[0].get("version")
        history = manifest.get("history", {})
        req_before = file_hash(os.path.join(HERE, "requirements.txt"))
        snap = os.path.join(PREVIOUS, rep["from"] or "unknown")
        shutil.rmtree(snap, ignore_errors=True)
        # keep at most three previous versions
        for old in previous_versions()[2:]:
            shutil.rmtree(os.path.join(PREVIOUS, old), ignore_errors=True)
        deferred = []   # VERSION and MANIFEST.json go last, so a failure mid-way leaves the old version stamped
        for rel, new_hash in sorted(manifest["files"].items()):
            if _untouchable(rel):
                continue
            src = os.path.join(root, *rel.split("/"))
            dst = os.path.join(HERE, *rel.split("/"))
            if not os.path.isfile(src):
                continue
            if rel in ("VERSION", "MANIFEST.json"):
                deferred.append((src, dst))
                continue
            local_hash = file_hash(dst)
            if rel.startswith("data/"):
                name = rel.split("/", 1)[1]
                if name == "alerts.json":
                    rep["added_rules"] += _merge_alerts(src, dst)
                elif local_hash is None:
                    _copy_file(src, dst)
                    rep["added_data"].append(rel)
                elif name in SHIPPED_DATA and local_hash != new_hash and \
                        local_hash in history.get(rel, []):
                    _keep_old(dst, rel, snap)
                    _copy_file(src, dst)
                    rep["refreshed_data"].append(rel)
                continue
            if local_hash == new_hash:
                rep["unchanged"] += 1
                continue
            if local_hash is not None and local_hash not in history.get(rel, []):
                rep["kept"].append(rel)      # changed on this computer: theirs to merge
                continue
            _keep_old(dst, rel, snap)
            _copy_file(src, dst)
            rep["copied"] += 1
        # the manifest never lists itself; VERSION and MANIFEST.json land last
        deferred.append((os.path.join(root, "MANIFEST.json"), os.path.join(HERE, "MANIFEST.json")))
        for src, dst in deferred:
            if os.path.isfile(src):
                _keep_old(dst, os.path.relpath(dst, HERE).replace(os.sep, "/"), snap)
                _copy_file(src, dst)
        req_after = file_hash(os.path.join(HERE, "requirements.txt"))
        if req_before != req_after:
            try:
                p = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                                    os.path.join(HERE, "requirements.txt")],
                                   capture_output=True, text=True, timeout=600, cwd=HERE)
                rep["pip"] = "ok" if p.returncode == 0 else "failed: " + (p.stderr or "")[-300:]
            except Exception as exc:  # noqa: BLE001
                rep["pip"] = "failed: " + str(exc)[:200]
        rep["ok"] = True
        rep["seconds"] = round(time.time() - started, 1)
        try:
            os.remove(CHECK_PATH)   # next look at GitHub starts clean
        except OSError:
            pass
    except Exception as exc:  # noqa: BLE001
        rep["error"] = str(exc)[:300]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        _state["busy"] = False
    try:
        _write_json(RESULT_PATH, rep)
    except OSError:
        pass
    return rep


def restart_soon(delay=1.5):
    """Replace this process with a fresh one on the same command line, so the
    new files take effect. Under the always-on service, or without it, the
    desk answers again within seconds; if the exec fails, exit and let the
    service bring it back."""
    def _go():
        time.sleep(delay)
        try:
            sys.stdout.flush(); sys.stderr.flush()
        except Exception:  # noqa: BLE001
            pass
        try:
            os.chdir(HERE)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:  # noqa: BLE001
            os._exit(0)
    threading.Thread(target=_go, daemon=True).start()


def loop(on_update=None):
    """Daily check in the background; applies it by itself when
    DESK_AUTO_UPDATE=on. Starts a minute after boot so a fresh install is
    not slowed down."""
    time.sleep(60)
    while True:
        try:
            c = check()
            if c.get("available") and auto_enabled() and not _state["busy"]:
                rep = apply()
                if rep.get("ok"):
                    if on_update:
                        on_update(rep)
                    restart_soon(3)
                    return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3600)


if __name__ == "__main__":
    # python updater.py check | apply | rollback [version] | previous
    import json as _json
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        print(_json.dumps(check(force=True), indent=2))
    elif cmd == "apply":
        print(_json.dumps(apply(), indent=2))
    elif cmd == "rollback":
        print(_json.dumps(rollback(sys.argv[2] if len(sys.argv) > 2 else None), indent=2))
    elif cmd == "previous":
        print("\n".join(previous_versions()) or "none kept")
    else:
        print(__doc__)
