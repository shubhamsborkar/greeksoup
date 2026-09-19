"""Build the documentation site: site/*.md -> docs/docs/**/index.html.

    python scripts/build_docs.py

Plain markdown in with a short front matter (title, description), one folder
per section, order from site/nav.json. Out comes a static site GitHub Pages
serves next to the landing page: one shell (top bar, sidebar, on-this-page
rail, previous and next, footer), a search index (search.json) the page
searches in the browser, and nothing that needs a server. Needs the
`markdown` package (pip install markdown); it is a build tool, not a desk
dependency, so it is not in requirements.txt.

Links inside pages are written as /docs/section/page/ and rewritten to
relative paths at build time, so the site works at greeksoup.ai/docs/ and at
the GitHub Pages address alike.
"""

import html
import json
import os
import re
import shutil
import sys
from datetime import date

try:
    import markdown
except ImportError:
    sys.exit("pip install markdown   (the build tool for the docs; not needed by the desk)")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "docs", "docs")
REPO = "https://github.com/shubhamsborkar/greeksoup"
SITE_NAME = "GreekSoup"
SITE_URL = "https://greeksoup.ai"


def version():
    try:
        with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as fh:
            return fh.readline().split()[0]
    except (OSError, IndexError):
        return ""


def front_matter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            for ln in text[3:end].strip().splitlines():
                k, _, v = ln.partition(":")
                meta[k.strip()] = v.strip().strip('"')
            text = text[end + 4:]
    return meta, text.lstrip("\n")


def render_md(text):
    md = markdown.Markdown(extensions=["extra", "admonition", "toc", "sane_lists", "md_in_html"],
                           extension_configs={"toc": {"toc_depth": "2-3", "permalink": False}})
    body = md.convert(text)
    return body, md.toc_tokens


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def load_nav():
    with open(os.path.join(SRC, "nav.json"), encoding="utf-8") as fh:
        return json.load(fh)["sections"]


def page_url(section_dir, page):
    return f"/docs/{section_dir}/" if page == "index" else f"/docs/{section_dir}/{page}/"


def out_path(section_dir, page):
    return os.path.join(OUT, section_dir, "index.html") if page == "index" else os.path.join(OUT, section_dir, page, "index.html")


def rel_prefix(url):
    """How many folders up from this page to /docs/."""
    depth = url.rstrip("/").count("/") - 1     # /docs/a/ -> 1, /docs/a/b/ -> 2
    return "../" * depth


def relativise(body, rel):
    body = body.replace('href="/docs/', f'href="{rel}')
    body = body.replace('src="/docs/', f'src="{rel}')
    body = body.replace('href="/img/', f'href="{rel}../img/')
    body = body.replace('src="/img/', f'src="{rel}../img/')
    body = body.replace('href="/install.sh"', f'href="{rel}../install.sh"')
    body = body.replace('href="/#', f'href="{rel}../#')
    body = body.replace('href="/"', f'href="{rel}../"')
    return body


def toc_html(tokens):
    if not tokens:
        return ""
    items = []
    for t in tokens:
        items.append(f'<li><a href="#{t["id"]}">{html.escape(t["name"])}</a></li>')
        for c in t.get("children", []):
            items.append(f'<li class="sub"><a href="#{c["id"]}">{html.escape(c["name"])}</a></li>')
    return "<ul>" + "".join(items) + "</ul>"


def sidebar_html(sections, pages, current_url, rel):
    out = []
    for sec in sections:
        out.append(f'<div class="sec"><div class="sec-t">{html.escape(sec["title"])}</div><ul>')
        for pg in sec["pages"]:
            p = pages[(sec["dir"], pg)]
            cls = ' class="on"' if p["url"] == current_url else ""
            out.append(f'<li{cls}><a href="{rel}{p["url"][len("/docs/"):]}">{html.escape(p["nav"])}</a></li>')
        out.append("</ul></div>")
    return "".join(out)


SHELL = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · {site} docs</title>
<meta name="description" content="{description}">
<meta property="og:title" content="{title} · {site} docs">
<meta property="og:description" content="{description}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="https://greeksoup.ai/img/og.jpg">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="{rel}../img/greeksoup-favicon-32.png" sizes="32x32"><link rel="apple-touch-icon" href="{rel}../img/greeksoup-favicon-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{rel}assets/docs.css">
<script>try{{var t=localStorage.getItem("gs-theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t;}}catch(e){{}}</script>
<!-- Cloudflare Web Analytics: counts page views and visits for greeksoup.ai, no cookie, no personal data --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "2e8be72dd4814f2e8301f4ffb36140e5"}}'></script>
</head>
<body data-rel="{rel}">
<a class="skip" href="#content">Skip to content</a>
<header class="top">
  <button class="menu" id="menu" aria-label="Open the contents"><span></span><span></span><span></span></button>
  <a class="brand" href="{rel}../" aria-label="GreekSoup, home"><svg class="gsm" viewBox="0 0 120 120" aria-hidden="true"><path d="M22 38l16 22-16 22" stroke="#ED5A24" stroke-width="12" stroke-linecap="square" stroke-linejoin="miter" fill="none"/><rect x="48" y="66" width="12" height="20"/><rect x="66" y="50" width="12" height="36"/><rect x="84" y="34" width="12" height="52"/></svg><span>greeksoup<b>/</b></span></a>
  <a class="docs-tag" href="{rel}">docs</a>
  <button class="search" id="search-open" aria-label="Search the docs"><svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="7" cy="7" r="4.6"/><path d="M10.5 10.5L14 14"/></svg><span>Search</span><kbd>⌘K</kbd></button>
  <nav class="links">
    <a href="{rel}../#install">Install</a>
    <a href="{rel}project/security/">Security</a>
    <button class="theme" id="theme" aria-label="Switch between light and dark"><svg class="sun" viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="8" cy="8" r="3.2"/><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4"/></svg><svg class="moon" viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M13.5 10.2A6 6 0 015.8 2.5a6 6 0 107.7 7.7z"/></svg></button>
    <a class="gh" href="{repo}" aria-label="GreekSoup on GitHub" title="GitHub"><svg viewBox="0 0 16 16"  fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg></a>
    <a class="gh" href="https://gitlab.com/shikshan-nivesh/greeksoup" aria-label="GreekSoup on GitLab, the mirror" title="GitLab mirror"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M22.65 14.39 12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z"/></svg></a>
    <a class="btn" href="{rel}../#install">Install</a>
  </nav>
</header>
<div class="frame">
  <aside class="side" id="side">
    <div class="side-in">{sidebar}</div>
  </aside>
  <div class="scrim" id="scrim"></div>
  <main class="content" id="content">
    <div class="crumb">{section}</div>
    <article class="prose">
      <h1>{title}</h1>
      {lead}
      {body}
    </article>
    <nav class="pn">
      {prev}
      {next}
    </nav>
    <footer class="foot">
      <span>{site}: the one-person equity research desk. A <a href="https://shikshannivesh.com">Shikshan Nivesh</a> product. For investors who refuse to settle.</span>
      <span class="mono">version {version} · built {built} · <a href="{edit}">edit this page</a></span>
    </footer>
  </main>
  <aside class="rail">
    {toc_block}
  </aside>
</div>
<div class="modal" id="modal" hidden>
  <div class="box" role="dialog" aria-label="Search the docs">
    <input id="q" placeholder="Search the docs…" autocomplete="off" spellcheck="false">
    <div class="hits" id="hits"></div>
    <div class="hint">↑↓ to move · Enter to open · Esc to close</div>
  </div>
</div>
<script src="{rel}assets/docs.js"></script>
</body>
</html>
"""


def build():
    sections = load_nav()
    pages = {}
    order = []
    for sec in sections:
        for pg in sec["pages"]:
            path = os.path.join(SRC, sec["dir"], pg + ".md")
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
            meta, text = front_matter(raw)
            body, toc = render_md(text)
            title = meta.get("title") or (toc[0]["name"] if toc else pg)
            entry = {"section": sec["title"], "dir": sec["dir"], "page": pg, "url": page_url(sec["dir"], pg),
                     "title": title, "nav": meta.get("nav") or title, "description": meta.get("description", ""),
                     "lead": meta.get("lead", ""), "body": body, "toc": toc, "src": os.path.relpath(path, ROOT),
                     "text": strip_tags(body)}
            pages[(sec["dir"], pg)] = entry
            order.append(entry)

    if os.path.isdir(OUT):
        for name in os.listdir(OUT):
            if name != "assets":
                p = os.path.join(OUT, name)
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    for asset in ("docs.css", "docs.js"):
        shutil.copyfile(os.path.join(SRC, "assets", asset), os.path.join(OUT, "assets", asset))

    ver, built = version(), date.today().isoformat()
    search = []
    for i, p in enumerate(order):
        rel = rel_prefix(p["url"])
        prev_ = order[i - 1] if i > 0 else None
        next_ = order[i + 1] if i + 1 < len(order) else None
        link = lambda q, cls, lab: (f'<a class="{cls}" href="{rel}{q["url"][len("/docs/"):]}"><small>{lab}</small><b>{html.escape(q["title"])}</b></a>' if q else "<span></span>")  # noqa: E731
        toc_block = ('<div class="rail-t">On this page</div>' + toc_html(p["toc"])) if len(p["toc"]) > 0 and (len(p["toc"]) > 1 or p["toc"][0].get("children")) else ""
        lead = f'<p class="lead">{p["lead"]}</p>' if p["lead"] else ""
        page = SHELL.format(
            title=html.escape(p["title"]), site=SITE_NAME, description=html.escape(p["description"] or strip_tags(p["lead"]) or p["title"]),
            canonical=SITE_URL + p["url"],
            rel=rel, repo=REPO, sidebar=sidebar_html(sections, pages, p["url"], rel), section=html.escape(p["section"]),
            lead=relativise(lead, rel), body=relativise(p["body"], rel), prev=link(prev_, "prev", "Previous"),
            next=link(next_, "next", "Next"), version=ver, built=built,
            edit=f"{REPO}/edit/main/{p['src']}", toc_block=toc_block)
        dest = out_path(p["dir"], p["page"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(page)
        search.append({"t": p["title"], "s": p["section"], "u": p["url"][len("/docs/"):],
                       "h": [t["name"] for t in p["toc"]] + [c["name"] for t in p["toc"] for c in t.get("children", [])],
                       "x": p["text"][:600]})

    # the docs home: site/index.md, rendered with the same shell but no rail
    with open(os.path.join(SRC, "index.md"), encoding="utf-8") as fh:
        meta, text = front_matter(fh.read())
    body, _ = render_md(text)
    home = SHELL.format(
        title=html.escape(meta.get("title", "Documentation")), site=SITE_NAME, description=html.escape(meta.get("description", "")),
        canonical=SITE_URL + "/docs/",
        rel="", repo=REPO, sidebar=sidebar_html(sections, pages, "/docs/", ""), section="Documentation",
        lead=(f'<p class="lead">{meta["lead"]}</p>' if meta.get("lead") else ""), body=relativise(body, ""),
        prev="<span></span>", next=(f'<a class="next" href="{order[0]["url"][len("/docs/"):]}"><small>Next</small><b>{html.escape(order[0]["title"])}</b></a>' if order else "<span></span>"),
        version=ver, built=built, edit=f"{REPO}/edit/main/site/index.md", toc_block="")
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(home)
    with open(os.path.join(OUT, "search.json"), "w", encoding="utf-8") as fh:
        json.dump(search, fh, ensure_ascii=False)
    write_discovery(sections, pages, order, built)
    print(f"docs: {len(order)} pages + home, version {ver}, into {os.path.relpath(OUT, ROOT)}/")


def write_discovery(sections, pages, order, built):
    """Three files at the site's root, for the machines that read it: the map every
    search engine asks for, the file that says everything here is open to read, and
    the plain-text index an answer engine or an AI agent reads instead of the HTML."""
    site = os.path.dirname(OUT)          # docs/, which is the site's root on Pages
    urls = [(SITE_URL + "/", "1.0"), (SITE_URL + "/docs/", "0.9")] + [(SITE_URL + p["url"], "0.8") for p in order]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, pri in urls:
        xml.append(f"  <url><loc>{url}</loc><lastmod>{built}</lastmod><priority>{pri}</priority></url>")
    xml.append("</urlset>")
    with open(os.path.join(site, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(xml) + "\n")

    with open(os.path.join(site, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write("# GreekSoup: the one-person equity research desk. Everything here is open to read.\n"
                 "User-agent: *\nAllow: /\n\n"
                 f"Sitemap: {SITE_URL}/sitemap.xml\n")

    lines = ["# GreekSoup",
             "",
             "> The one-person equity research desk: fourteen screens that read your broker, the filings, the "
             "options tape and the public record, running on your own computer. Open source under the MIT licence, "
             "your keys stay with you, and it places no orders. Twelve of the fourteen screens run with no key at all.",
             "",
             "Installed with one line on Mac, Windows or Linux. Six brokers connect read-only as it comes and any "
             "other is one file written to a contract in the repository. Nothing here needs an account, and no page "
             "on this site is behind a login.",
             ""]
    for sec in sections:
        lines.append(f"## {sec['title']}")
        lines.append("")
        for pg in sec["pages"]:
            p = pages[(sec["dir"], pg)]
            desc = strip_tags(p["description"] or p["lead"]).strip()
            lines.append(f"- [{p['title']}]({SITE_URL}{p['url']}): {desc}")
        lines.append("")
    lines += ["## Elsewhere", "",
              f"- [The landing page]({SITE_URL}/): what the desk is, the fourteen screens, and the one-line install.",
              f"- [The repository]({REPO}): the whole desk, MIT licensed.",
              f"- [What changed, newest first]({REPO}/blob/main/VERSION): the same file the desk reads when it checks for an update.",
              ""]
    with open(os.path.join(site, "llms.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    build()
