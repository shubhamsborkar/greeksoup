"""Publish the plugins in plugins/ as the public list the desk's Settings reads: one zip per
plugin and docs/plugins/index.json (name, what it adds, who wrote it, what it talks to, the
zip). Run before scripts/build_docs.py; the list ships with the site on greeksoup.ai."""
import json
import os
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "plugins")
OUT = os.path.join(HERE, "docs", "plugins")
SITE = "https://greeksoup.ai/plugins/"

os.makedirs(OUT, exist_ok=True)
rows = []
for name in sorted(os.listdir(SRC)):
    folder = os.path.join(SRC, name)
    meta_path = os.path.join(folder, "plugin.json")
    if not os.path.isfile(meta_path):
        continue
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    adds = []
    if meta.get("screen"):
        adds.append("a screen")
    if meta.get("blocks"):
        adds.append("blocks")
    if meta.get("door"):
        adds.append("a door")
    zpath = os.path.join(OUT, f"{name}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _dirs, files in os.walk(folder):
            for f in sorted(files):
                if f.startswith("."):
                    continue
                full = os.path.join(dirpath, f)
                z.write(full, os.path.join(name, os.path.relpath(full, folder)))
    rows.append({"name": meta.get("name", name), "label": meta.get("label", name), "version": str(meta.get("version", "")),
                 "author": meta.get("author", ""), "what": meta.get("what", ""), "talks_to": meta.get("talks_to", []),
                 "adds": adds, "zip": SITE + f"{name}.zip", "size": os.path.getsize(zpath)})
with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
    json.dump({"list": "GreekSoup plugins", "plugins": rows}, fh, indent=1)
print("docs/plugins/index.json:", len(rows), "plugins")
