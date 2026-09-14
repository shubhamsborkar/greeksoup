/* GreekSoup docs: theme, the contents drawer on a phone, copy buttons on
   code, tabs, the on-this-page rail, and a search that runs in the browser
   over search.json. No framework, nothing fetched but that one file. */
"use strict";
(function () {
  const rel = document.body.dataset.rel || "";
  let store = { getItem: () => null, setItem: () => {} };
  try { store = window.localStorage; } catch (e) { /* private mode */ }

  /* theme */
  const themeBtn = document.getElementById("theme");
  if (themeBtn) themeBtn.onclick = () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { store.setItem("gs_docs_theme", next); } catch (e) { /* ignore */ }
  };

  /* contents drawer */
  const menu = document.getElementById("menu"), scrim = document.getElementById("scrim");
  if (menu) menu.onclick = () => document.body.classList.toggle("side-open");
  if (scrim) scrim.onclick = () => document.body.classList.remove("side-open");
  /* keep the current page in view inside the contents, scrolling only that
     column: a scrollIntoView here would drag the whole page toward the
     drawer on a phone, where the drawer sits off-screen */
  const side = document.getElementById("side"), on = document.querySelector(".side li.on");
  if (side && on) side.scrollTop = Math.max(0, on.offsetTop - side.clientHeight / 2);

  /* copy buttons */
  document.querySelectorAll(".prose pre").forEach(pre => {
    const b = document.createElement("button");
    b.className = "copy"; b.type = "button"; b.textContent = "Copy";
    b.onclick = async () => {
      const code = pre.querySelector("code");
      const text = (code ? code.innerText : pre.innerText).replace(/\n$/, "");
      try { await navigator.clipboard.writeText(text); b.textContent = "Copied"; b.classList.add("done"); }
      catch (e) { b.textContent = "Select and copy"; }
      setTimeout(() => { b.textContent = "Copy"; b.classList.remove("done"); }, 1600);
    };
    pre.appendChild(b);
  });

  /* tabs: <div class="tabs"><div class="tabbar"><button>..</button></div><div class="pane">..</div></div> */
  document.querySelectorAll(".tabs").forEach(t => {
    const btns = t.querySelectorAll(".tabbar button"), panes = t.querySelectorAll(".pane");
    const pick = i => { btns.forEach((b, j) => b.classList.toggle("on", i === j)); panes.forEach((p, j) => p.classList.toggle("on", i === j)); };
    btns.forEach((b, i) => b.onclick = () => pick(i));
    pick(0);
  });

  /* on-this-page: light the heading in view */
  const railLinks = [...document.querySelectorAll(".rail li a")];
  if (railLinks.length) {
    const heads = railLinks.map(a => document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)))).filter(Boolean);
    const mark = () => {
      let cur = heads[0];
      for (const h of heads) if (h.getBoundingClientRect().top < 120) cur = h;
      railLinks.forEach(a => a.parentElement.classList.toggle("here", cur && a.getAttribute("href") === "#" + cur.id));
    };
    document.addEventListener("scroll", mark, { passive: true }); mark();
  }

  /* search */
  const modal = document.getElementById("modal"), q = document.getElementById("q"), hits = document.getElementById("hits");
  let index = null, sel = 0, rows = [];
  const open = () => { modal.hidden = false; q.value = ""; hits.innerHTML = ""; q.focus(); if (!index) fetch(rel + "search.json").then(r => r.json()).then(d => { index = d; }); };
  const close = () => { modal.hidden = true; };
  const esc = s => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const snippet = (text, words) => {
    const lower = text.toLowerCase();
    let at = -1;
    for (const w of words) { at = lower.indexOf(w); if (at >= 0) break; }
    const start = Math.max(0, at - 60), out = text.slice(start, start + 170);
    let h = esc((start ? "…" : "") + out + (start + 170 < text.length ? "…" : ""));
    for (const w of words) if (w.length > 1) h = h.replace(new RegExp("(" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>");
    return h;
  };
  const run = () => {
    const words = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!index || !words.length) { hits.innerHTML = ""; rows = []; return; }
    rows = index.map(p => {
      const t = p.t.toLowerCase(), h = p.h.join(" ").toLowerCase(), x = p.x.toLowerCase();
      let score = 0;
      for (const w of words) {
        if (t.includes(w)) score += 8; if (h.includes(w)) score += 4; if (x.includes(w)) score += 1;
        if (!t.includes(w) && !h.includes(w) && !x.includes(w)) score -= 20;
      }
      return { p, score };
    }).filter(r => r.score > 0).sort((a, b) => b.score - a.score).slice(0, 8);
    sel = 0;
    hits.innerHTML = rows.length ? rows.map((r, i) =>
      `<a class="hit ${i === 0 ? "sel" : ""}" href="${rel}${r.p.u}"><small>${esc(r.p.s)}</small><b>${esc(r.p.t)}</b><span>${snippet(r.p.x, words)}</span></a>`).join("")
      : '<div class="none">Nothing matches. Try another word, or the word as it appears on the screen.</div>';
  };
  if (modal) {
    document.getElementById("search-open").onclick = open;
    modal.onclick = e => { if (e.target === modal) close(); };
    q.oninput = run;
    document.addEventListener("keydown", e => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); modal.hidden ? open() : close(); return; }
      if (modal.hidden) return;
      if (e.key === "Escape") close();
      else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); if (!rows.length) return;
        sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + rows.length) % rows.length;
        hits.querySelectorAll(".hit").forEach((h, i) => h.classList.toggle("sel", i === sel));
      } else if (e.key === "Enter" && rows.length) { location.href = rel + rows[sel].p.u; }
    });
  }
})();
