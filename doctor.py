"""Check this desk and print what an AI agent needs to fix it.

    python doctor.py            the full check, including a few small network probes
    python doctor.py --offline  the same without touching the network

Prints plain lines, never a key, never a position. Copy everything it prints
and give it to your agent, or paste it into a bug report.
"""
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OFFLINE = "--offline" in sys.argv
OK, WARN, BAD = "ok  ", "look", "fix "
lines = []
problems = 0


def say(mark, text):
    global problems
    if mark == BAD:
        problems += 1
    lines.append(f"[{mark}] {text}")
    print(lines[-1])


def read_env():
    env = {}
    path = os.path.join(HERE, ".env")
    if not os.path.isfile(path):
        return None
    for raw in open(path, encoding="utf-8", errors="replace"):
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main():
    print("GreekSoup check,", time.strftime("%Y-%m-%d %H:%M"))
    print()

    # the computer
    say(OK, f"{platform.system()} {platform.release()}, {platform.machine()}")
    v = sys.version_info
    if v >= (3, 10):
        say(OK, f"Python {v.major}.{v.minor}.{v.micro} at {sys.executable}")
    else:
        say(BAD, f"Python {v.major}.{v.minor} is too old; the desk needs 3.10 or newer")

    # the folder
    if os.path.isfile(os.path.join(HERE, "server.py")):
        say(OK, f"desk folder: {HERE}")
    else:
        say(BAD, f"this is not the desk folder (no server.py here): {HERE}")
        return problems
    venv = os.path.join(HERE, ".venv")
    # A folder with the desk's files but no settings and no environment is the
    # repository as it comes off GitHub, not a desk somebody installed. Nothing
    # in it is broken, so the missing pieces below are said plainly, not as faults.
    installed = os.path.isfile(os.path.join(HERE, ".env")) or os.path.isdir(venv)
    if not installed:
        say(OK, "these are the desk's files, and no desk is installed here yet (no settings file, no environment), so this check reports what is present and nothing is marked wrong")
    if os.path.isdir(venv):
        say(OK, "the desk's own Python environment (.venv) is present")
        in_venv = os.path.abspath(sys.prefix).startswith(os.path.abspath(venv))
        if not in_venv:
            say(WARN, "this check is not running inside .venv; the desk itself does, so a missing package below may be a false alarm")
    else:
        say(BAD if installed else OK, "no .venv folder" + ("; run the install line again or tell your agent to create it" if installed else ""))
    for pkg in ("requests", "dotenv", "certifi"):
        try:
            __import__(pkg)
            say(OK, f"package {pkg} imports")
        except Exception:  # noqa: BLE001
            say(WARN, f"package {pkg} did not import in this Python")

    # the version
    try:
        first = next(l for l in open(os.path.join(HERE, "VERSION"), encoding="utf-8") if l.strip() and not l.startswith("#"))
        say(OK, "version " + first.split()[0])
    except Exception:  # noqa: BLE001
        say(WARN, "VERSION file missing or empty")
    chk = os.path.join(HERE, "cache", "update_check.json")
    if os.path.isfile(chk):
        try:
            c = json.load(open(chk, encoding="utf-8"))
            age = (time.time() - c.get("at", 0)) / 3600
            say(OK, f"last look at GitHub {age:.0f} hours ago; newer version available: {'yes, ' + str(c.get('remote')) if c.get('available') else 'no'}")
        except Exception:  # noqa: BLE001
            say(WARN, "the update check file could not be read")
    else:
        say(OK, "no update check recorded yet (the first one runs a minute after the desk starts)")

    # the settings, names only
    env = read_env()
    if env is None:
        say(BAD if installed else OK, "no .env file" + ("; the Settings screen writes it, or copy .env.example to .env" if installed else "; the install line writes one"))
        env = {}
    else:
        say(OK, ".env present")
    port = env.get("DESK_PORT") or "8765"
    broker = env.get("BROKER") or "(none)"
    say(OK, f"broker: {broker}; home market: {env.get('HOME_MARKET') or '(follows the broker)'}")
    keys_set = sorted(k for k, val in env.items() if val and (k.endswith(("_KEY", "_SECRET", "_TOKEN")) or k in ("FMP_API_KEY", "DATA_API_KEY", "AI_API_KEY")))
    say(OK, "keys set (names only): " + (", ".join(keys_set) if keys_set else "none; twelve of the fourteen screens run without one"))
    say(OK, f"data provider: {env.get('DATA_PROVIDER') or '(none)'}; AI: {env.get('AI_PROVIDER') or '(none)'}; auto-update: {env.get('DESK_AUTO_UPDATE') or 'off'}")

    # is it running
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=3) as r:
            say(OK, f"the desk answers at http://localhost:{port} (status {r.status})")
    except Exception as exc:  # noqa: BLE001
        if installed:
            say(BAD, f"nothing answers at http://localhost:{port} ({type(exc).__name__}); double-click Start Desk, or read the log lines below")
        else:
            say(OK, f"nothing answers at http://localhost:{port}, which is what a folder with no desk installed in it looks like")
        s = socket.socket()
        s.settimeout(1)
        try:
            if s.connect_ex(("127.0.0.1", int(port))) == 0:
                say(WARN, f"something else is listening on port {port}; change DESK_PORT in .env or stop that program")
        except Exception:  # noqa: BLE001
            pass
        finally:
            s.close()

    # the always-on entry
    # An entry exists for THIS folder only when it names this folder: a reader with
    # two copies of the desk must not be told the other copy's entry is theirs.
    def spellings():
        """This folder in every form Windows may have written it: as given, long
        (C:\\Users\\runneradmin) and short (C:\\Users\\RUNNER~1)."""
        out = {os.path.abspath(HERE)}
        if os.name == "nt":
            try:
                import ctypes
                for fn in (ctypes.windll.kernel32.GetLongPathNameW, ctypes.windll.kernel32.GetShortPathNameW):
                    buf = ctypes.create_unicode_buffer(1024)
                    if fn(os.path.abspath(HERE), buf, 1024):
                        out.add(buf.value)
            except Exception:  # noqa: BLE001
                pass
        return {x.rstrip("\\").lower() for x in out}

    def mine(text):
        return bool(text) and any(sp in text.lower() for sp in spellings())

    def read(path):
        try:
            return open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            return ""

    system = platform.system() if installed else ""
    if system == "Darwin":
        plist = os.path.expanduser("~/Library/LaunchAgents/com.research-desk.plist")
        if mine(read(plist)):
            say(OK, "start-at-login entry present, and it points at this folder")
        elif os.path.isfile(plist):
            say(WARN, "a start-at-login entry exists but it points at another copy of the desk; double-click Keep Desk Running in this folder to point it here")
        else:
            say(WARN, "start-at-login entry absent; double-click Keep Desk Running to add it")
    elif system == "Linux":
        unit = os.path.expanduser("~/.config/systemd/user/greeksoup-desk.service")
        if mine(read(unit)):
            say(OK, "start-at-login entry present, and it points at this folder")
        elif os.path.isfile(unit):
            say(WARN, "a start-at-login entry exists but it points at another copy of the desk")
        else:
            say(WARN, "start-at-login entry absent; the install line adds it, or run Keep Desk Running")
    elif system == "Windows":
        # Either a scheduled task or, on PCs that refuse one, a shortcut in the user's
        # Startup folder. The shortcut is a binary file with its arguments in UTF-16.
        lnk = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "GreekSoup Desk.lnk")
        lnk_mine = False
        try:
            if os.path.isfile(lnk):
                raw = open(lnk, "rb").read().lower()
                lnk_mine = any(sp.encode(enc) in raw for sp in spellings() for enc in ("utf-16-le", "mbcs"))
        except (OSError, LookupError):
            pass
        try:
            p = subprocess.run(["schtasks", "/Query", "/TN", "Research Desk", "/XML"], capture_output=True, text=True, timeout=10)
            if p.returncode == 0 and mine(p.stdout):
                say(OK, "start-at-login task present, and it points at this folder")
            elif lnk_mine:
                say(OK, "start-at-login shortcut present in the Startup folder, and it points at this folder")
            elif p.returncode == 0:
                say(WARN, "a start-at-login task exists but it points at another copy of the desk")
            elif os.path.isfile(lnk):
                say(WARN, "a Startup shortcut exists but it points at another copy of the desk")
            else:
                say(WARN, "start-at-login entry absent; double-click Keep Desk Running.bat to add it")
        except Exception:  # noqa: BLE001
            say(OK if lnk_mine else WARN, "start-at-login shortcut present in the Startup folder" if lnk_mine else "could not query the scheduled task")

    # disk and folders
    try:
        free = shutil.disk_usage(HERE).free / 1e9
        say(OK if free > 1 else WARN, f"{free:.1f} GB free on this disk")
    except Exception:  # noqa: BLE001
        pass
    for folder in ("data", "cache", "logs"):
        path = os.path.join(HERE, folder)
        if os.path.isdir(path):
            size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(path) for f in fs) / 1e6
            say(OK, f"{folder}/ {size:.0f} MB")
        else:
            say(WARN if folder == "data" else OK, f"{folder}/ absent")

    # the last errors in the log
    for log in ("desk-service.log", "desk.log"):
        path = os.path.join(HERE, "logs", log)
        if not os.path.isfile(path):
            continue
        try:
            tail = open(path, encoding="utf-8", errors="replace").read()[-20000:].splitlines()
        except Exception:  # noqa: BLE001
            continue
        bad = [l for l in tail if any(w in l for w in ("Traceback", "Error", "error", "refused", "Exception"))][-8:]
        say(OK, f"logs/{log}: {len(tail)} recent lines" + ("; the last error lines follow" if bad else "; no error lines in the tail"))
        for l in bad:
            print("      " + l[:200])

    # the network, small and anonymous
    if not OFFLINE:
        probes = [("GitHub (the version check)", "https://raw.githubusercontent.com/shubhamsborkar/one-person-equity-research-desk/main/VERSION"),
                  ("SEC EDGAR", "https://www.sec.gov/"),
                  ("Yahoo Finance quotes", "https://query1.finance.yahoo.com/"),
                  ("FRED", "https://fred.stlouisfed.org/")]
        for label, url in probes:
            try:
                req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "GreekSoup doctor"})
                with urllib.request.urlopen(req, timeout=6) as r:
                    say(OK, f"{label} reachable ({r.status})")
            except urllib.error.HTTPError as exc:
                say(OK if exc.code < 500 else WARN, f"{label} answered {exc.code}")
            except Exception as exc:  # noqa: BLE001
                say(WARN, f"{label} not reachable from here ({type(exc).__name__})")

    print()
    if problems:
        print(f"{problems} thing(s) marked [fix ]. Copy everything above and give it to your AI agent with: 'Read README.md in this folder, then fix what the check found.'")
    elif not installed:
        print("Nothing to fix. These are the desk's files; to install a desk here, read the Install section of README.md.")
    else:
        print("Nothing to fix. If a screen still looks wrong, copy everything above into a bug report or give it to your agent.")
    return problems


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
