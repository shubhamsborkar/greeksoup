"""Tag the release at the top of VERSION and publish it on GitHub's Releases page.

    python scripts/github_release.py

Runs after the push. The tag is the version string (2026-09-15.33), the release
title is the same, and the notes are the VERSION line, so the Releases page on
GitHub carries what the desk's own update strip and greeksoup.ai/docs/project/releases/
already carry. Re-running for a version that is already tagged and published does
nothing. The token comes from git's own credential store for the remote's user,
never from the environment or a file here.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, check=check).stdout.strip()


def main():
    first = open(os.path.join(HERE, "VERSION"), encoding="utf-8").readline().rstrip("\n")
    m = re.match(r"^(\d{4}-\d{2}-\d{2}\.\d+)\s+(.*)$", first)
    if not m:
        sys.exit("VERSION's first line is not '<date>.<n>  <notes>'")
    version, notes = m.group(1), m.group(2).strip()

    remote = git("remote", "get-url", "origin")
    rm = re.match(r"https://(?:([^@]+)@)?github\.com/([^/]+)/([^/.]+)(?:\.git)?$", remote)
    if not rm:
        sys.exit(f"origin is not an https GitHub remote: {remote}")
    user, owner, repo = rm.group(1) or rm.group(2), rm.group(2), rm.group(3)

    if git("tag", "-l", version) != version:
        git("tag", "-a", version, "-m", notes)
        print("tagged", version)
    git("push", "origin", version)

    fill = subprocess.run(["git", "credential", "fill"], input=f"protocol=https\nhost=github.com\nusername={user}\n\n",
                          capture_output=True, text=True, check=True).stdout
    token = next((l.split("=", 1)[1] for l in fill.splitlines() if l.startswith("password=")), "")
    if not token:
        sys.exit("no GitHub credential stored for " + user)

    api = f"https://api.github.com/repos/{owner}/{repo}/releases"
    hdr = ["-H", f"Authorization: Bearer {token}", "-H", "Accept: application/vnd.github+json"]
    have = subprocess.run(["curl", "-s", *hdr, f"{api}/tags/{version}"], capture_output=True, text=True).stdout
    if json.loads(have or "{}").get("tag_name") == version:
        print("already published:", json.loads(have)["html_url"])
        return
    body = json.dumps({"tag_name": version, "name": version, "body": notes, "draft": False, "prerelease": False})
    out = subprocess.run(["curl", "-s", "-X", "POST", *hdr, "-H", "Content-Type: application/json", "-d", body, api],
                         capture_output=True, text=True).stdout
    d = json.loads(out or "{}")
    if "html_url" not in d:
        sys.exit("GitHub refused the release: " + d.get("message", out[:300]))
    print("published:", d["html_url"])


if __name__ == "__main__":
    main()
