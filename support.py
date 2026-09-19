"""Tell us, the sending half. A report a reader writes on /report can go straight to us:
the desk posts it to our support address (a small script on Cloudflare, source in
support/worker.js), which files it as a public issue on the repository and hands back
the number and the link. The reply we write on that issue comes back into the desk
here, so the reader is answered where they already are, and the next reader with the
same problem finds it by search. Nothing is sent until the reader presses Send, and
the reader sees every line that goes.

SUPPORT_URL empty means the route is not switched on in this version: the page keeps
the Email it button and says so.
"""

import json
import os
import threading
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS_PATH = os.path.join(HERE, "data", "reports.json")   # the reader's own: which reports this desk sent
REPO = "shubhamsborkar/greeksoup"
SUPPORT_URL = (os.getenv("DESK_SUPPORT_URL") or "").strip() or "https://greeksoup-support.mute-cloud-a367.workers.dev/report"
FRESH = 600            # seconds a fetched issue is kept before the desk asks GitHub again
_lock = threading.Lock()
_cache = {}            # number -> (fetched_at, issue view)


def enabled():
    return bool(SUPPORT_URL)


def _read():
    try:
        with open(REPORTS_PATH, encoding="utf-8") as fh:
            d = json.load(fh)
            return d if isinstance(d, dict) else {"reports": []}
    except (OSError, ValueError):
        return {"reports": []}


def _write(d):
    os.makedirs(os.path.dirname(REPORTS_PATH), exist_ok=True)
    tmp = REPORTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
    os.replace(tmp, REPORTS_PATH)


def send(what, check, screen, version, email=""):
    """Post one report. Returns {ok, number, url} or {ok: False, error}."""
    if not enabled():
        return {"ok": False, "error": "Sending straight from the desk is not switched on in this version. Email it instead; the button beside this one opens your mail app with the same report."}
    what = (what or "").strip()
    if not what:
        return {"ok": False, "error": "Write a line about what happened first."}
    body = {"what": what[:4000], "check": (check or "")[:12000], "screen": (screen or "")[:200],
            "version": (version or "")[:40], "email": (email or "").strip()[:200]}
    try:
        r = requests.post(SUPPORT_URL, json=body, timeout=30,
                          headers={"User-Agent": "greeksoup-desk"})
    except requests.RequestException as exc:
        return {"ok": False, "error": f"The report did not leave: the support address did not answer ({type(exc).__name__}). Check the connection and press Send again, or Email it instead."}
    if r.status_code == 429:
        return {"ok": False, "error": "Too many reports from this address in the last hour. Wait a while, or Email it instead."}
    if r.status_code != 200:
        return {"ok": False, "error": f"The support address answered {r.status_code}. Press Send again in a minute, or Email it instead."}
    try:
        out = r.json()
    except ValueError:
        return {"ok": False, "error": "The support address answered with something the desk could not read. Email it instead."}
    if not out.get("ok"):
        return {"ok": False, "error": (out.get("error") or "the support address refused the report") + ". Email it instead."}
    with _lock:
        d = _read()
        d["reports"].insert(0, {"number": out["number"], "url": out["url"], "title": what.split("\n")[0][:80],
                                "at": time.strftime("%Y-%m-%d %H:%M"), "seen_comments": 0})
        _write(d)
    return {"ok": True, "number": out["number"], "url": out["url"]}


def _fetch(number):
    """One issue's public view, from GitHub, cached. No token: the issue is public."""
    now = time.time()
    with _lock:
        hit = _cache.get(number)
    if hit and now - hit[0] < FRESH:
        return hit[1]
    view = None
    try:
        r = requests.get(f"https://api.github.com/repos/{REPO}/issues/{number}", timeout=12,
                         headers={"Accept": "application/vnd.github+json", "User-Agent": "greeksoup-desk"})
        if r.status_code == 200:
            j = r.json()
            view = {"state": j.get("state"), "comments": j.get("comments", 0), "url": j.get("html_url"), "last": None}
            if view["comments"]:
                c = requests.get(f"https://api.github.com/repos/{REPO}/issues/{number}/comments?per_page=1&sort=created&direction=desc",
                                 timeout=12, headers={"Accept": "application/vnd.github+json", "User-Agent": "greeksoup-desk"})
                if c.status_code == 200 and c.json():
                    last = c.json()[0]
                    view["last"] = {"who": (last.get("user") or {}).get("login", ""), "at": (last.get("created_at") or "")[:10],
                                    "text": (last.get("body") or "")[:600]}
    except requests.RequestException:
        pass
    if view is not None:
        with _lock:
            _cache[number] = (now, view)
    return view or (hit[1] if hit else None)


def listing(light=False):
    """The reports this desk sent, each with its public state. `light` skips GitHub."""
    d = _read()
    out = []
    waiting = 0
    for rep in d["reports"][:30]:
        row = dict(rep)
        if not light:
            v = _fetch(rep["number"])
            if v:
                row.update({"state": v["state"], "comments": v["comments"], "last": v["last"]})
                row["new"] = v["comments"] > rep.get("seen_comments", 0)
                waiting += 1 if row["new"] else 0
        out.append(row)
    return {"enabled": enabled(), "reports": out, "waiting": waiting}


def seen(number):
    with _lock:
        d = _read()
        for rep in d["reports"]:
            if rep["number"] == number:
                v = _cache.get(number)
                rep["seen_comments"] = v[1]["comments"] if v else rep.get("seen_comments", 0)
        _write(d)
    return {"ok": True}
