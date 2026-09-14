"""Write site/project/releases.md from VERSION, so the docs carry the same
release list the desk itself reads. Run before scripts/build_docs.py."""
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def nice_date(v):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:\.(\d+))?$", v)
    if not m:
        return v
    y, mo, d, n = m.groups()
    s = f"{int(d)} {MONTHS[int(mo) - 1]} {y}"
    return s + (f", release {n}" if n else "")


rows = []
for line in open(os.path.join(HERE, "VERSION"), encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    parts = line.split(None, 1)
    rows.append((parts[0], parts[1] if len(parts) > 1 else ""))

out = ["---", "title: Releases", "nav: Releases",
       "description: What changed in GreekSoup, newest first, read from the same VERSION file your desk reads when it checks for an update.",
       f"lead: Newest first. The current version is {rows[0][0]}. Your desk reads this same list once a day and offers the update with one click.",
       "---", ""]
for v, note in rows:
    out.append(f"## {v}")
    out.append("")
    out.append(f"*{nice_date(v)}.* {note}")
    out.append("")
os.makedirs(os.path.join(HERE, "site", "project"), exist_ok=True)
with open(os.path.join(HERE, "site", "project", "releases.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("site/project/releases.md:", len(rows), "releases")
