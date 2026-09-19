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

# Hosting files and the one-line installers are not the desk. The installers run once, on
# install day, from greeksoup.ai; inside an update they are a liability: on 2026-09-19 a
# reader's Bitdefender read the unpacked docs/install.ps1 as a downloader (it fetches a zip
# and runs winget, which is what one looks like), locked it, and the update died on it.
SKIP = {"MANIFEST.json", ".gitignore", ".gitlab-ci.yml", "netlify.toml",
        "install.sh", "install.ps1"}
# The website (the launch page, its images and video, and the docs source) is served by
# GitHub Pages, not by the desk, so a reader's copy never needs any of it in an update.
SKIP_DIRS = ("site/", "docs/")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


SHIP_EXT = (".py", ".html", ".js", ".css", ".json", ".md", ".txt", ".sh", ".ps1", ".plist")


def unstaged_ship_files():
    """Program files that would ship but are not staged: a modified tracked file whose change
    is only in the working copy, or a new file never added. The manifest hashes the index, so
    a release made with these outstanding stamps the new version on the old code (2026-09-15.22
    did exactly that: chains.py never left the author's machine)."""
    out = []
    for line in git("status", "--porcelain", "--untracked-files=all").splitlines():
        code, rel = line[:2], line[3:].strip()
        if rel.startswith(SKIP_DIRS) or rel in SKIP or not rel.endswith(SHIP_EXT):
            continue
        if rel.startswith("data/") and code != "??":
            continue          # the author's own book and lists; the shipped copies are the staged ones
        if code[1] == "M" or code == "??":
            out.append(rel)
    return out


def main():
    version = (parse_version_text(open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read())
               or [{"version": ""}])[0]["version"]
    # what this release touches that a reader may hold edited data in: the owners of
    # reader-owned files and the shipped starters; the author reads this before it ships
    try:
        sys.path.insert(0, ROOT)
        import migrate as desk_migrate
        staged = set(git("diff", "--cached", "--name-only", "HEAD").splitlines())
        touched = sorted(staged & (set(desk_migrate.owners()) | set(desk_migrate.STARTERS)))
        bad = desk_migrate.check_registry()
        if bad:
            print("MANIFEST.json NOT written. A reader-owned file's format rose with no migration:\n  " + "\n  ".join(bad))
            sys.exit(2)
        if touched:
            print("This release touches files readers hold edited copies of, or the code that writes them:\n  " +
                  "\n  ".join(touched) + "\n  If a file's shape changed: FORMAT up, a migration registered, a test. "
                  "If a starter changed: readers who edited theirs keep theirs.")
    except ImportError:
        pass
    loose = unstaged_ship_files()
    if loose and "--anyway" not in sys.argv:
        print("MANIFEST.json NOT written. These files would ship but are not staged, so the manifest "
              "would stamp the new version on old code:\n  " + "\n  ".join(loose) +
              "\nStage them by name (git add <file>) and run this again; --anyway skips the check.")
        sys.exit(2)
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
            if rel in SKIP or rel.startswith(SKIP_DIRS):
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
