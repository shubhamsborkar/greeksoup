"""Write MANIFEST.json for a release. Run from the repository root before
committing a version bump:

    python scripts/make_manifest.py

`files`   : sha256 of every tracked file as it stands in the working tree
            (line endings folded), data/ included.
`history` : for every path, every hash it has ever shipped with, read from
            every commit on the branch plus the working tree. The updater on
            a reader's machine uses this to tell "unchanged since some
            release" (safe to overwrite) from "changed on this computer"
            (kept, listed for the agent to merge). Readers who installed
            before MANIFEST.json existed are covered by the same history.
"""

import json
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from updater import bytes_hash, parse_version_text  # noqa: E402

SKIP = {"MANIFEST.json", ".gitignore"}
# The website (the landing page's docs and their source) is served by GitHub
# Pages, not by the desk, so a reader's copy never needs it in an update.
SKIP_DIRS = ("site/", "docs/docs/")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def main():
    version = (parse_version_text(open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read())
               or [{"version": ""}])[0]["version"]
    tracked = [p for p in git("ls-files").splitlines()
               if p and p not in SKIP and not p.startswith(SKIP_DIRS)]
    files = {}
    for rel in tracked:
        # Hash what is staged to ship, never the working copy: on the author's own
        # machine a data file can hold his book while the shipped file is the example.
        files[rel] = bytes_hash(subprocess.check_output(["git", "show", f":{rel}"], cwd=ROOT))

    history = {rel: {h} for rel, h in files.items()}
    blob_hash = {}
    commits = git("rev-list", "--all").split()
    for c in commits:
        for line in git("ls-tree", "-r", c).splitlines():
            meta, rel = line.split("\t", 1)
            blob = meta.split()[2]
            if rel in SKIP:
                continue
            if blob not in blob_hash:
                content = subprocess.check_output(["git", "cat-file", "-p", blob], cwd=ROOT)
                blob_hash[blob] = bytes_hash(content)
            history.setdefault(rel, set()).add(blob_hash[blob])

    out = {"version": version,
           "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "commits_scanned": len(commits),
           "files": files,
           "history": {k: sorted(v) for k, v in sorted(history.items())}}
    with open(os.path.join(ROOT, "MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print(f"MANIFEST.json: version {version}, {len(files)} files, "
          f"{sum(len(v) for v in history.values())} historical hashes from {len(commits)} commits")


if __name__ == "__main__":
    main()
