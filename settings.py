"""The Settings screen's back end: the desk writes the reader's key file (.env)
so nobody opens it by hand, checks a data key against the feed, and switches
"start with the computer" on or off.

Rules kept here:
  - only the keys in ALLOWED are ever written; anything else in the body is dropped
  - a key is never sent back to the page in full, only its last four characters
  - the update never touches .env (see updater.NEVER_TOUCH), so what is saved here
    survives every new version
"""

import json
import os
import platform
import subprocess
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
EXAMPLE_PATH = os.path.join(HERE, ".env.example")

# name -> (secret?, one-line meaning). Every broker file adds its own fields.
ALLOWED = {
    "BROKER": (False, "which broker file Desk · Home reads through"),
    "HOME_MARKET": (False, "the home market file, when no broker sets it"),
    "DATA_PROVIDER": (False, "fmp, or the name of a provider module the reader's agent wrote"),
    "FMP_API_KEY": (True, "Financial Modeling Prep key, optional"),
    "DATA_API_KEY": (True, "another data provider's key, optional"),
    "DATA_BASE_URL": (False, "another data provider's address, optional"),
    "AI_PROVIDER": (False, "which AI provider preset"),
    "AI_FORMAT": (False, "openai or anthropic: the request shape the endpoint speaks"),
    "AI_API_KEY": (True, "AI key, optional"),
    "AI_MODEL": (False, "model name at that provider"),
    "AI_BASE_URL": (False, "address of the endpoint (local models too)"),
    "EDGAR_CONTACT": (False, "the e-mail the SEC asks for on every request"),
    "DESK_AUTO_UPDATE": (False, "on: bring a newer version in without the click"),
    "SCREENS": (False, "screens you chose to show or hide in the sidebar (key:on or key:off); the rest follow the home market"),
    "JOURNAL": (False, "ask (the default), always or never: how the journal takes the moments the desk sees"),
    "RESEARCH_DIR": (False, "where the research vault lives when not in data/research: a folder inside a drive you already sync"),
    "RISK_BENCHMARK": (False, "the index the home book is measured against on Risk, a Yahoo symbol; empty follows the home market"),
    "RISK_BENCHMARK_LABEL": (False, "what Risk calls that index"),
    "GUIDE": (False, "done once the reader closes the startup guide; empty shows it"),
    "GUIDE_TICKS": (False, "the guide's steps the reader ticked by hand"),
}
try:
    import brokers as _brokers
    for _m in _brokers.all_meta():
        for _f in _m["fields"]:
            ALLOWED[_f["env"]] = (bool(_f.get("secret")), f"{_m['label']}: {_f['label']}")
except Exception:  # noqa: BLE001 - the key file still works without the broker list
    pass


# ---- the key file ------------------------------------------------------------
def read_env():
    """The values saved in .env (not the process environment): what the page shows."""
    out = {}
    if not os.path.exists(ENV_PATH):
        return out
    try:
        with open(ENV_PATH, encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def write_env(updates):
    """Set or add KEY=value lines, keeping every comment and every other line.
    Creates .env from .env.example on a copy that never had one. Then reloads
    the process environment so the change applies without a restart."""
    updates = {k: str(v).strip() for k, v in updates.items() if k in ALLOWED}
    if not updates:
        return []
    lines = []
    src = ENV_PATH if os.path.exists(ENV_PATH) else (EXAMPLE_PATH if os.path.exists(EXAMPLE_PATH) else None)
    if src:
        with open(src, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    done = set()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k = s.split("=", 1)[0].strip()
        if k in updates and k not in done:
            lines[i] = f"{k}={updates[k]}"
            done.add(k)
    for k, v in updates.items():
        if k not in done:
            lines.append(f"{k}={v}")
    tmp = ENV_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines).rstrip("\n") + "\n")
    os.replace(tmp, ENV_PATH)
    # only the changed names touch the running process; nothing else in the
    # environment (the port the service set, say) is re-read
    for k, v in updates.items():
        if v:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)
    return sorted(updates)


def _real(v):
    """A saved value that is not one of the example file's placeholders."""
    v = (v or "").strip()
    if not v or v.startswith(("your_", "paste_")) or v == "your-email@example.com":
        return ""
    return v


def masked(v):
    v = _real(v)
    if not v:
        return ""
    return "ends in " + v[-4:] if len(v) > 6 else "saved"


def current():
    """What the page shows: which keys exist, never the keys themselves."""
    env = read_env()
    g = lambda k: _real(env.get(k) or os.getenv(k, ""))  # noqa: E731
    provider = (g("DATA_PROVIDER") or ("fmp" if g("FMP_API_KEY") else "")).lower()
    return {
        "data": {"provider": provider, "key": masked(g("FMP_API_KEY")),
                 "other_key": masked(g("DATA_API_KEY")), "other_base": g("DATA_BASE_URL"),
                 "other_name": g("DATA_PROVIDER") if provider not in ("", "fmp") else ""},
        "ai": {"provider": g("AI_PROVIDER") or "", "format": g("AI_FORMAT") or "", "key": masked(g("AI_API_KEY")),
               "model": g("AI_MODEL"), "base_url": g("AI_BASE_URL")},
        "edgar_contact": g("EDGAR_CONTACT"),
        "risk_benchmark": g("RISK_BENCHMARK"), "risk_benchmark_label": g("RISK_BENCHMARK_LABEL"),
        "home_market": (g("HOME_MARKET") or "").lower(),
        "auto_update": (env.get("DESK_AUTO_UPDATE") or os.getenv("DESK_AUTO_UPDATE", "off")).strip().lower() == "on",
        "journal": ((env.get("JOURNAL") or os.getenv("JOURNAL", "ask")).strip().lower() or "ask"),
        "env_exists": os.path.exists(ENV_PATH),
    }


# ---- the reader's investing profile ------------------------------------------
# What the reader tells the desk about how they invest. Read by the /agent page
# (so any AI reading the desk knows who it is working for) and by the desk's own
# AI screens. Plain file, data/profile.json, the reader's to edit.
DATA_DIR = os.path.join(HERE, "data")
PROFILE_PATH = os.path.join(DATA_DIR, "profile.json")
PROFILE_LISTS = ("styles", "drivers", "sectors")
PROFILE_TEXT = ("risk", "horizon", "home_currency", "since", "about")
PROFILE_CHOICES = {
    "styles": ["Value", "Growth", "Quality", "Dividend", "Momentum", "Index", "Special situations", "Quant"],
    "drivers": ["Valuation", "Revenue growth", "Margins", "Free cash flow", "Return on equity", "Debt",
                "Management", "Moat", "Insider buying", "Capital allocation"],
    "risk": ["Conservative", "Moderate", "Aggressive"],
    "horizon": ["Weeks", "Months", "One to three years", "Three to ten years", "Longer"],
}


def load_profile():
    try:
        with open(PROFILE_PATH, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        d = {}
    out = {k: [str(x) for x in (d.get(k) or []) if str(x).strip()][:30] for k in PROFILE_LISTS}
    for k in PROFILE_TEXT:
        out[k] = str(d.get(k) or "").strip()[:600]
    return out


def save_profile(body):
    cur = load_profile()
    for k in PROFILE_LISTS:
        if k in body and isinstance(body[k], list):
            cur[k] = [str(x).strip()[:40] for x in body[k] if str(x).strip()][:30]
    for k in PROFILE_TEXT:
        if k in body and isinstance(body[k], str):
            cur[k] = body[k].strip()[:600]
    cur["home_currency"] = cur["home_currency"].upper()[:8]
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = PROFILE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"_comment": "How you invest, from the Settings screen. The agent page carries it.", **cur}, fh, indent=2)
    os.replace(tmp, PROFILE_PATH)
    return cur


def profile_text():
    """The profile as plain lines for the /agent page; empty string when nothing is set."""
    p = load_profile()
    lines = []
    if p["styles"]:
        lines.append("Investing style: " + ", ".join(p["styles"]))
    if p["drivers"]:
        lines.append("Looks at first: " + ", ".join(p["drivers"]))
    if p["sectors"]:
        lines.append("Sectors followed: " + ", ".join(p["sectors"]))
    if p["risk"]:
        lines.append("Risk appetite: " + p["risk"])
    if p["horizon"]:
        lines.append("Holding period: " + p["horizon"])
    if p["home_currency"]:
        lines.append("Home currency: " + p["home_currency"])
    if p["since"]:
        lines.append("Investing since: " + p["since"])
    if p["about"]:
        lines.append("In the reader's words: " + p["about"])
    return "\n".join(lines)


# ---- the reader's files: where they are, and a backup ------------------------
def data_files():
    """The files under data/ with a plain name and size, for the Settings screen."""
    rows = []
    try:
        for name in sorted(os.listdir(DATA_DIR)):
            path = os.path.join(DATA_DIR, name)
            if not os.path.isfile(path) or name.startswith("."):
                continue
            what = ""
            try:
                with open(path, encoding="utf-8") as fh:
                    head = json.load(fh)
                what = (head.get("_comment") if isinstance(head, dict) else "") or ""
            except (OSError, ValueError):
                pass
            first = what.split(". ")[0].strip()
            rows.append({"file": name, "what": (first + ".") if first and not first.endswith(".") else first,
                         "bytes": os.path.getsize(path)})
    except OSError:
        pass
    return rows


def restore_zip(data):
    """A backup back in: every file under data/ in the zip is written into place. A file that
    is about to change is kept first under cache/previous/restore-<stamp>/, so a restore can
    itself be undone by hand, and the report says what was written and what was kept. Paths
    that would leave data/ are refused; nothing else in the zip is touched."""
    import io
    import zipfile
    from datetime import datetime
    if not data or len(data) > 500 * 1024 * 1024:
        raise ValueError("the zip is empty or larger than the desk takes (500 MB)")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("that is not a zip file")
    names = [n for n in z.namelist() if not n.endswith("/")]
    if any(n.startswith("/") or ".." in n.split("/") or "\\" in n for n in names):
        raise ValueError("the zip reaches outside the desk folder; refused")
    wanted = [n for n in names if n.startswith("data/") and n.split("/")[-1] not in (".env",) and not n.split("/")[-1].startswith(".")]
    if not wanted:
        raise ValueError("no data/ folder in the zip: this is not a desk backup")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    kept_dir = os.path.join(HERE, "cache", "previous", f"restore-{stamp}")
    written, kept, same = [], [], 0
    import notes as desk_notes
    for n in wanted:
        blob = z.read(n)
        if n.startswith("data/research/"):
            dst = os.path.join(desk_notes.RESEARCH_DIR, *n[len("data/research/"):].split("/"))
        else:
            dst = os.path.join(HERE, *n.split("/"))
        if os.path.isfile(dst):
            with open(dst, "rb") as fh:
                cur = fh.read()
            if cur == blob:
                same += 1
                continue
            keep = os.path.join(kept_dir, *n.split("/"))
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            with open(keep, "wb") as fh:
                fh.write(cur)
            kept.append(n)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(blob)
        written.append(n)
    return {"written": written, "kept": kept, "unchanged": same, "kept_in": kept_dir if kept else ""}


def backup_zip():
    """A zip of data/ (and research/ when it exists): lists, book, profile, alerts.
    Never the key file, never the daily tokens, never the downloaded caches."""
    import io
    import zipfile
    import notes as desk_notes
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for top in ("data", "research"):
            root = os.path.join(HERE, top)
            if not os.path.isdir(root):
                continue
            for dirpath, _dirs, files in os.walk(root):
                for f in files:
                    if f.startswith(".") or f.endswith(".tmp"):
                        continue
                    full = os.path.join(dirpath, f)
                    zf.write(full, os.path.relpath(full, HERE))
        vault = os.path.abspath(desk_notes.RESEARCH_DIR)
        if os.path.isdir(vault) and not vault.startswith(os.path.abspath(HERE) + os.sep):
            # the vault lives in a synced folder outside the desk: it goes in under data/research all the same
            for dirpath, _dirs, files in os.walk(vault):
                if os.path.relpath(dirpath, vault).split(os.sep)[0] == "index":
                    continue
                for f in files:
                    if f.startswith(".") or f.endswith(".tmp"):
                        continue
                    full = os.path.join(dirpath, f)
                    zf.write(full, os.path.join("data", "research", os.path.relpath(full, vault)))
    return buf.getvalue()


# ---- the data key check ------------------------------------------------------
# What the desk asks the feed for, in the reader's words, and one request that
# shows whether the key's plan answers it.
FMP_PROBES = [
    ("Company profile and quotes", "profile", {"symbol": "AAPL"}),
    ("Financial statements", "income-statement", {"symbol": "AAPL", "limit": 1}),
    ("Analyst estimates", "analyst-estimates", {"symbol": "AAPL", "period": "annual", "limit": 1}),
    ("Revenue by segment", "revenue-product-segmentation", {"symbol": "AAPL"}),
    ("Peers, dividends and news", "stock-peers", {"symbol": "AAPL"}),
    ("Market-wide insider scan", "insider-trading/latest", {"limit": 1}),
    ("Senate trading disclosures", "senate-latest", {"limit": 1}),
    ("Price history for the 50 and 200 day columns", "historical-price-eod/light", {"symbol": "AAPL"}),
]


def check_fmp(key=None):
    key = (key or os.getenv("FMP_API_KEY", "")).strip()
    if not key:
        return {"ok": False, "error": "No data key saved yet."}
    rows, valid = [], None
    for label, path, params in FMP_PROBES:
        params = dict(params, apikey=key)
        try:
            r = requests.get(f"https://financialmodelingprep.com/stable/{path}", params=params, timeout=12)
            code = r.status_code
        except Exception:  # noqa: BLE001
            rows.append({"what": label, "answer": "did not answer (network)"})
            continue
        if code == 200:
            body = None
            try:
                body = r.json()
            except ValueError:
                pass
            has = bool(body) and not (isinstance(body, dict) and body.get("Error Message"))
            rows.append({"what": label, "answer": "yes" if has else "answered, but empty"})
            valid = True if valid is None else valid
        elif code == 401:
            rows.append({"what": label, "answer": "key rejected"})
            valid = False
        elif code in (402, 403):
            rows.append({"what": label, "answer": "not in this key's plan"})
            valid = True if valid is None else valid
        elif code == 429:
            rows.append({"what": label, "answer": "rate limited, try again in a minute"})
        else:
            rows.append({"what": label, "answer": f"no answer ({code})"})
    if valid is False:
        return {"ok": False, "error": "The feed rejected this key. Check it on your account page at financialmodelingprep.com.", "rows": rows}
    yes = sum(1 for r in rows if r["answer"] == "yes")
    return {"ok": True, "rows": rows,
            "summary": f"The key works. {yes} of {len(rows)} things the desk asks for come back on this plan."}


# ---- start with the computer -------------------------------------------------
MAC_LABEL = "com.research-desk"
LINUX_UNIT = "greeksoup-desk.service"
WIN_TASK = "Research Desk"


def _run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20, **kw)
    except Exception:  # noqa: BLE001
        return None


def _mac_plist():
    return os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents", MAC_LABEL + ".plist")


def _linux_unit():
    return os.path.join(os.path.expanduser("~"), ".config", "systemd", "user", LINUX_UNIT)


def _owned(text):
    """True when a service definition points at THIS folder. Two copies of the
    desk on one computer share the service name; the switch on one copy must
    never touch the other's."""
    return HERE in (text or "")


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


_ON = "On. The desk starts when you log in and comes back by itself if it stops."
_OFF = "Off. The desk runs only while its window is open."
_LATER = "Off from your next login. The desk keeps running until then."
_OTHER = "Another copy of the desk on this computer owns the login service, so the switch here stays out of the way."


def autostart_status():
    """{'state': 'on'|'off'|'other'|'unknown', 'text': plain words}"""
    sysname = platform.system()
    if sysname == "Darwin":
        uid = os.getuid()
        loaded = _run(["launchctl", "print", f"gui/{uid}/{MAC_LABEL}"])
        loaded_text = (loaded.stdout if loaded and loaded.returncode == 0 else "")
        plist = _read(_mac_plist())
        if plist and not _owned(plist):
            return {"state": "other", "text": _OTHER}
        if loaded_text and not _owned(loaded_text):
            return {"state": "other", "text": _OTHER}
        if loaded_text and plist:
            return {"state": "on", "text": _ON}
        if loaded_text and not plist:
            return {"state": "off", "text": _LATER}
        if os.getppid() == 1:
            return {"state": "other", "text": "The desk is kept running by a service set up outside this screen, so the switch here stays out of the way."}
        return {"state": "off", "text": _OFF}
    if sysname == "Linux":
        unit = _read(_linux_unit())
        if unit and not _owned(unit):
            return {"state": "other", "text": _OTHER}
        r = _run(["systemctl", "--user", "is-enabled", LINUX_UNIT])
        if r and r.returncode == 0:
            return {"state": "on", "text": _ON}
        return {"state": "off", "text": _OFF}
    if sysname == "Windows":
        r = _run(["schtasks", "/Query", "/TN", WIN_TASK, "/XML"])
        if r and r.returncode == 0:
            return {"state": "on", "text": _ON} if _owned(r.stdout) else {"state": "other", "text": _OTHER}
        return {"state": "off", "text": _OFF}
    return {"state": "unknown", "text": "Not available on this system."}


def set_autostart(on):
    """Register or remove the login service the same way the Keep Desk Running
    files do. Switching off never stops the desk that is running now."""
    sysname = platform.system()
    py = sys.executable
    if autostart_status()["state"] == "other":
        return {"ok": False, "error": _OTHER}
    if sysname == "Darwin":
        plist = _mac_plist()
        uid = os.getuid()
        if on:
            os.makedirs(os.path.dirname(plist), exist_ok=True)
            os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
            log = os.path.join(HERE, "logs", "desk-service.log")
            with open(plist, "w", encoding="utf-8") as fh:
                fh.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{MAC_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{py}</string>
    <string>server.py</string>
  </array>
  <key>WorkingDirectory</key><string>{HERE}</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
""")
            loaded = _run(["launchctl", "print", f"gui/{uid}/{MAC_LABEL}"])
            if not (loaded and loaded.returncode == 0):
                r = _run(["launchctl", "bootstrap", f"gui/{uid}", plist])
                if r is None or r.returncode != 0:
                    return {"ok": False, "error": (r.stderr if r else "launchctl did not answer").strip() or "could not register the service"}
            return {"ok": True, "text": "On from now. If a Start Desk window is open, close it; the service takes over within ten seconds."}
        try:
            if os.path.exists(plist):
                os.remove(plist)
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "text": "Off from your next login. The desk keeps running until then."}
    if sysname == "Linux":
        unit = _linux_unit()
        unit_dir = os.path.dirname(unit)
        if on:
            os.makedirs(unit_dir, exist_ok=True)
            with open(unit, "w", encoding="utf-8") as fh:
                fh.write(f"[Unit]\nDescription=GreekSoup desk\n[Service]\nExecStart={py} server.py\n"
                         f"WorkingDirectory={HERE}\nRestart=always\nRestartSec=5\n[Install]\nWantedBy=default.target\n")
            _run(["systemctl", "--user", "daemon-reload"])
            r = _run(["systemctl", "--user", "enable", LINUX_UNIT])
            if r is None or r.returncode != 0:
                return {"ok": False, "error": (r.stderr if r else "systemctl did not answer").strip()}
            return {"ok": True, "text": "On from your next login. The desk you are using now keeps running."}
        r = _run(["systemctl", "--user", "disable", LINUX_UNIT])
        return {"ok": True, "text": "Off from your next login. The desk keeps running until then."}
    if sysname == "Windows":
        if on:
            script = os.path.join(HERE, "desk-service.ps1")
            r = _run(["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", WIN_TASK, "/RL", "LIMITED", "/TR",
                      f'powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{script}"'])
            if r is None or r.returncode != 0:
                return {"ok": False, "error": (r.stderr or r.stdout if r else "schtasks did not answer").strip()}
            return {"ok": True, "text": "On from your next login. The desk you are using now keeps running."}
        _run(["schtasks", "/Delete", "/TN", WIN_TASK, "/F"])
        return {"ok": True, "text": "Off from your next login. The desk keeps running until then."}
    return {"ok": False, "error": "Not available on this system."}
