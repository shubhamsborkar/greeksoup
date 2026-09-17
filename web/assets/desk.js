/* GreekSoup desk — shared chrome. The ONE nav list (now a sidebar rail: adding a
   tab here adds it on every page), the theme switcher, the Cmd-K command
   palette and the bottom alert bar. Active tab is derived from the URL,
   including the ?list= regions of /watch. */
"use strict";
(function () {
  /* ---- persisted chrome state, applied before first paint ---------------- */
  const THEMES = ["graphite", "alpha"];
  let store = { getItem: () => null, setItem: () => {} };
  try { store = window.localStorage; } catch (e) { /* file:// etc. */ }
  const savedTheme = store.getItem("desk_theme");
  if (THEMES.includes(savedTheme)) document.documentElement.dataset.theme = savedTheme;
  let rail = store.getItem("desk_rail");
  if (rail !== "min" && rail !== "full") rail = window.innerWidth < 900 ? "min" : "full";
  document.documentElement.dataset.rail = rail;

  /* ---- the ONE tab list: [href, label, group, icon] ---------------------- */
  const I = {
    deskin: '<path d="M2.5 2.5h11v11h-11z"/><path d="M8 2.5v11M2.5 8h11"/>',
    deskus: '<path d="M8 1.5v13"/><path d="M11 3.5H6.8a2 2 0 000 4h2.4a2 2 0 010 4H5"/>',
    risk: '<path d="M2.5 11.5a5.5 5.5 0 0111 0"/><path d="M8 11.5l2.6-3.6"/>',
    calendar: '<rect x="2.5" y="3.5" width="11" height="10" rx="1.5"/><path d="M2.5 6.5h11M5.5 2v3M10.5 2v3"/><path d="M5.5 9.5h1M8 9.5h1M10.5 9.5h1"/>',
    watch: '<path d="M1.8 8s2.3-4.2 6.2-4.2S14.2 8 14.2 8s-2.3 4.2-6.2 4.2S1.8 8 1.8 8z"/><circle cx="8" cy="8" r="1.9"/>',
    list: '<path d="M5.4 4h9M5.4 8h9M5.4 12h9"/><path d="M2 4h.01M2 8h.01M2 12h.01"/>',
    globe: '<circle cx="8" cy="8" r="6.2"/><path d="M1.8 8h12.4"/><path d="M8 1.8c1.9 1.7 2.7 3.9 2.7 6.2S9.9 12.5 8 14.2c-1.9-1.7-2.7-3.9-2.7-6.2S6.1 3.5 8 1.8z"/>',
    macro: '<path d="M2.5 13.5V9M6.2 13.5V4.5M9.9 13.5V7M13.6 13.5V2.5"/>',
    funds: '<rect x="2" y="5" width="12" height="8.5" rx="1.5"/><path d="M5.5 5V3.6A1.1 1.1 0 016.6 2.5h2.8a1.1 1.1 0 011.1 1.1V5"/>',
    flow: '<path d="M8.8 1.5L3.5 9h3.7l-1 5.5L11.5 7H7.8z"/>',
    short: '<path d="M2 4.5l4.6 4.6 2.6-2.6 4.8 4.8"/><path d="M14 8.5v2.8h-2.8"/>',
    capitol: '<path d="M2.5 13.5h11"/><path d="M4 13.5V7m2.7 6.5V7m2.6 6.5V7m2.7 6.5V7"/><path d="M2.5 7L8 2.5 13.5 7z"/>',
    chain: '<circle cx="3.5" cy="12" r="1.8"/><circle cx="8" cy="4" r="1.8"/><circle cx="12.5" cy="12" r="1.8"/><path d="M4.5 10.4L7 5.8m2 0l2.5 4.6M5.3 12h5.4"/>',
    commods: '<path d="M3 5.5l5-3 5 3v5l-5 3-5-3z"/><path d="M3 5.5l5 3 5-3M8 8.5v5"/>',
    book: '<path d="M3 2.5h7.5a2 2 0 012 2v9H5a2 2 0 01-2-2z"/><path d="M3 11.5a2 2 0 012-2h7.5"/><path d="M6 5.5h4"/>',
    notes: '<path d="M3.5 2.5h7l2.5 2.5v8.5h-9.5z"/><path d="M10.5 2.5V5H13"/><path d="M5.5 8h5M5.5 10.5h3.5"/>',
    settings: '<circle cx="8" cy="8" r="2.2"/><path d="M8 1.8v2M8 12.2v2M1.8 8h2M12.2 8h2M3.6 3.6l1.4 1.4M11 11l1.4 1.4M3.6 12.4L5 11M11 5l1.4-1.4"/>',
  };
  const TABS = [
    /* [href, label, group, icon, key]. "Home" is your broker account (whatever market), "US" is the US public-record desk. Rename here. */
    ["/", "Desk · Home", "Desks", I.deskin, "home"],   // carries the US panels too, for every reader
    ["/book", "Desk · Book", "Desks", I.book, "book"],
    ["/risk", "Risk", "Desks", I.risk, "risk"],
    ["/watch", "Watch · Home", "Watchlists", I.watch, "watch"],
    ["/watch?list=us", "Watch · US", "Watchlists", I.list, "watchus"],
    ["/watch?list=global", "Global", "Watchlists", I.globe, "global"],
    ["/funds", "Funds", "Intelligence", I.funds, "funds"],
    ["/flow", "Flow", "Intelligence", I.flow, "flow"],
    ["/short", "Short", "Intelligence", I.short, "short"],
    ["/capitol", "Capitol", "Intelligence", I.capitol, "capitol"],
    ["/calendar", "Calendar", "Intelligence", I.calendar, "calendar"],
    ["/macro", "Macro", "Market", I.macro, "macro"],
    ["/commods", "Commodities", "Market", I.commods, "commods"],
    ["/chain", "Chain", "Market", I.chain, "chain"],
    ["/notes", "Notes", "Research", I.notes, "notes"],
    ["/settings", "Settings", "Setup", I.settings, "settings"],
  ];
  /* Screens the reader hid, or the home market hides for them. The last answer from
     /api/nav is kept in this browser so the rail paints right on the first frame, and
     the desk is asked again on every page for the current truth. */
  const FIXED = new Set(["home", "settings"]);
  let PLUGIN_TABS = [];   // screens that plugins add, from /api/nav: [href, label, group, icon, key]
  try { PLUGIN_TABS = JSON.parse(store.getItem("desk_plugin_tabs") || "[]"); } catch (e) { /* first visit */ }
  const PLUG_ICON = '<path d="M5 2.5v3M11 2.5v3"/><path d="M3.5 5.5h9v3a4.5 4.5 0 01-9 0z"/><path d="M8 13v1.5"/>';
  const allTabs = () => TABS.concat(PLUGIN_TABS);
  let hidden = new Set();
  try { hidden = new Set(JSON.parse(store.getItem("desk_hidden") || "[]")); } catch (e) { /* first visit */ }
  const HIDE_ICON = '<path d="M4 4l8 8M12 4l-8 8"/>';
  const EXPAND_ICON = '<path d="M9.5 2.5h4v4M13.5 2.5L9 7M6.5 13.5h-4v-4M2.5 13.5L7 9"/>';
  const SHRINK_ICON = '<path d="M13.5 6.5h-4v-4M9.5 6.5L14 2M2.5 9.5h4v4M6.5 9.5L2 14"/>';
  function current() {
    const p = location.pathname;
    if (p === "/watch") {
      const l = new URLSearchParams(location.search).get("list");
      return l === "us" ? "/watch?list=us" : l === "global" ? "/watch?list=global" : "/watch";
    }
    return p === "/index.html" ? "/" : p;
  }
  const svg = d => `<svg viewBox="0 0 16 16" aria-hidden="true">${d}</svg>`;
  // the GreekSoup mark: a prompt caret and three rising bars (a prompt and a tape); the bars take the ink, the caret stays orange
  const MARK_SVG = '<svg viewBox="0 0 120 120" aria-hidden="true"><path d="M22 38l16 22-16 22" stroke="#ED5A24" stroke-width="12" stroke-linecap="square" stroke-linejoin="miter" fill="none"/><rect x="48" y="66" width="12" height="20"/><rect x="66" y="50" width="12" height="36"/><rect x="84" y="34" width="12" height="52"/></svg>';

  /* ---- sidebar rail ------------------------------------------------------ */
  function buildRail() {
    const old = document.getElementById("siderail");
    if (old) old.remove();
    const cur = current();
    const groups = [];
    for (const [href, label, group, icon, key] of allTabs()) {
      if (hidden.has(key) && href !== cur) continue;   // the page you are on always shows in the rail
      let g = groups[groups.length - 1];
      if (!g || g.name !== group) { g = { name: group, items: [] }; groups.push(g); }
      g.items.push({ href, label, icon, key, on: href === cur });
    }
    // whatever is hidden stays in the rail, dimmed, under its own heading, with Show one click away:
    // hiding is never a one-way door
    const gone = allTabs().filter(([href, , , , key]) => hidden.has(key) && href !== cur);
    const el = document.createElement("aside");
    el.id = "siderail";
    el.innerHTML =
      '<a class="rbrand" href="/"><span class="rlogo">' + MARK_SVG + '</span>' +
      '<span class="rname">GREEK<b>SOUP</b><small>equity research desk</small></span></a>' +
      '<div class="rgroups">' +
      groups.map(g =>
        `<div class="rgt">${g.name}</div>` +
        g.items.map(it =>
          `<a class="rlink${it.on ? " on" : ""}" href="${it.href}" title="${it.label}" data-key="${it.key}">` +
          `${svg(it.icon)}<span>${it.label}</span>` +
          (FIXED.has(it.key) ? "" : `<button class="rhide" data-key="${it.key}" title="Hide ${it.label} from the sidebar. It moves to Hidden, below, and one click brings it back.">${svg(HIDE_ICON)}</button>`) +
          `</a>`).join("")
      ).join("") +
      '</div>' +
      (gone.length ? `<div class="rhiddenbox"><div class="rgt rgt-hidden">Hidden</div>` + gone.map(([href, label, , icon, key]) =>
        `<button class="rlink rgone" data-key="${key}" title="Show ${label} in the sidebar again">${svg(icon)}<span>${label}</span><em>show</em></button>`).join("") + '</div>' : "") +
      '<div class="rfoot">' +
      '<button id="askbtn" title="Ask SuperAnalyst, the desk\'s AI, about this screen (⌘I)"><span class="rk">✦</span><span>Ask SuperAnalyst</span></button>' +
      '<button id="cmdkbtn" title="Jump anywhere (⌘K)"><span class="rk">⌘</span><span>Command · K</span></button>' +
      '<button id="fbbtn" title="Tell us what is wrong, missing or unsupported on this screen"><span class="rk">✎</span><span>Feedback</span></button>' +
      '<button id="themebtn" title="Cycle theme"><span class="rk">◐</span><span>Theme · <b id="themename"></b></span></button>' +
      '<button id="railbtn" title="Collapse sidebar ( [ )"><span class="rk" id="railglyph">⟨</span><span>Collapse</span></button>' +
      '</div>' +
      '<button id="railedge" title="Collapse / expand the sidebar ( [ )">‹</button>';
    document.body.prepend(el);
    el.querySelectorAll(".rhide").forEach(b => b.onclick = e => {
      e.preventDefault(); e.stopPropagation();
      setShown(b.dataset.key, false);
      const label = (allTabs().find(t => t[4] === b.dataset.key) || [])[1] || "Screen";
      railToast(`${label} hidden. `, "Undo", () => setShown(b.dataset.key, true));
    });
    el.querySelectorAll(".rgone").forEach(b => b.onclick = e => { e.preventDefault(); setShown(b.dataset.key, true); });
    document.getElementById("railbtn").onclick = toggleRail;
    document.getElementById("railedge").onclick = toggleRail;
    document.getElementById("fbbtn").onclick = () => window.open(feedbackUrl("", ""), "_blank", "noopener");
    document.getElementById("cmdkbtn").onclick = () => openCmdk(true);
    document.getElementById("askbtn").onclick = () => openAsk(true);
    const tb = document.getElementById("themebtn");
    tb.onclick = () => {
      const curT = document.documentElement.dataset.theme || "graphite";
      const next = THEMES[(THEMES.indexOf(curT) + 1) % THEMES.length];
      document.documentElement.dataset.theme = next;
      store.setItem("desk_theme", next);
      syncFoot();
    };
    syncFoot();
  }
  async function setShown(key, show) {
    if (show) hidden.delete(key); else hidden.add(key);
    store.setItem("desk_hidden", JSON.stringify([...hidden]));
    buildRail();
    try {
      const r = await fetch("/api/settings/screens", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key, show }) });
      const d = await r.json(); if (d.nav) applyNav(d.nav);
    } catch (err) { /* offline: the browser copy stands until the next page load */ }
  }
  let toastTimer = null;
  function railToast(text, action, onAction) {
    const old = document.getElementById("railtoast"); if (old) old.remove();
    const t = document.createElement("div");
    t.id = "railtoast";
    t.innerHTML = `<span>${esc(text)}</span><button type="button">${esc(action)}</button>`;
    t.querySelector("button").onclick = () => { t.remove(); onAction(); };
    document.body.appendChild(t);
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.remove(), 8000);
  }
  window.deskToast = railToast;   // a page's own undo (a deleted chain, a removed name) uses the same strip
  /* ---- the startup guide: five steps bottom right on the first opens, each a link to the
     exact place; a step ticks itself when the desk can see it is done, or by hand. Done closes
     it; it comes back from Settings (This desk) and from the ⌘K palette. ------------------- */
  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }).then(r => r.json());
  let guideData = null;
  function renderGuide(g) {
    guideData = g;
    let el = document.getElementById("guide");
    if (!g || !g.shown) { if (el) el.remove(); return; }
    if (!el) { el = document.createElement("aside"); el.id = "guide"; document.body.appendChild(el); }
    const done = g.steps.filter(s => s.done).length;
    const v = g.vault || {};
    let vaultPick = "";
    if (!g.steps[0].done) {
      vaultPick = `<div class="gv"><div class="gvp">Now: <span class="mono">${esc(v.path)}</span></div><div class="gvb">` +
        `<button type="button" data-v="keep">Keep it here</button>` +
        `<button type="button" data-v="${esc(v.documents)}">Documents › GreekSoup</button>` +
        (v.synced || []).map(s => `<button type="button" data-v="${esc(s.path)}">${esc(s.label)} › GreekSoup</button>`).join("") +
        `<button type="button" data-v="other">Another folder…</button></div></div>`;
    }
    el.innerHTML = `<div class="gh"><b>Getting started</b><span class="gc">${done} of ${g.steps.length}</span><button type="button" class="gx" title="Close for now">×</button></div>` +
      g.steps.map((s, i) => `<div class="gs ${s.done ? "done" : ""}"><label class="gt"><input type="checkbox" data-k="${s.key}" ${s.done ? "checked" : ""}><span></span></label>` +
        `<div class="gb"><a href="${esc(s.href)}">${i + 1}. ${esc(s.label)}</a><div class="gtx">${esc(s.text)}</div>${i === 0 ? vaultPick : ""}</div></div>`).join("") +
      `<div class="gf"><button type="button" class="gdone">Done, hide this</button><span class="gn">Comes back from Settings, under This desk.</span></div>`;
    el.querySelector(".gx").onclick = () => { el.remove(); try { sessionStorage.setItem("guide_hidden", "1"); } catch (e) { /* fine */ } };
    el.querySelector(".gdone").onclick = async () => { renderGuide(await post("/api/guide", { done: true })); };
    el.querySelectorAll("input[data-k]").forEach(i => i.onchange = async () => { renderGuide(await post("/api/guide", { tick: i.dataset.k, on: i.checked })); });
    el.querySelectorAll("[data-v]").forEach(b => b.onclick = async () => {
      let target = b.dataset.v;
      if (target === "keep") { renderGuide(await post("/api/guide", { tick: "vault", on: true })); return; }
      if (target === "other") { target = prompt("The folder where your research should live (it is made if it is not there):", v.documents || ""); if (!target) return; }
      b.disabled = true; b.textContent = "Moving…";
      const out = await post("/api/research/relocate", { path: target });
      if (!out.ok) { alert(out.error || "That did not work."); renderGuide(g); return; }
      railToast(`Your research now lives in ${out.location ? out.location.path : target}. Bring it back is on Settings.`, "OK", () => {});
      renderGuide(await post("/api/guide", { tick: "vault", on: true }));
    });
  }
  async function loadGuide() {
    try { if (sessionStorage.getItem("guide_hidden")) return; } catch (e) { /* fine */ }
    try { renderGuide(await (await fetch("/api/guide", { cache: "no-store" })).json()); } catch (e) { /* the guide is a nicety */ }
  }
  window.deskGuide = { show: async () => { try { sessionStorage.removeItem("guide_hidden"); } catch (e) { /* fine */ } renderGuide(await post("/api/guide", { again: true })); } };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", loadGuide); else loadGuide();
  /* ---- the row menu: wherever a name appears as a link to its ticker page, a small ⋯ appears on
     hover with the next thing to do from here: open it, add it to a watchlist, a note on it, a
     task, put it on a chain, ask the AI about it. One component; no page has to know. ------- */
  (function () {
    let dot = null, pop = null, cur = null;
    function nameOf(a) {
      const u = new URL(a.getAttribute("href"), location.origin);
      const symbol = (u.searchParams.get("symbol") || "").toUpperCase();
      const region = (u.searchParams.get("region") || "us").toLowerCase();
      return symbol ? { symbol, region: region === "us" ? "us" : region === "global" ? "global" : "home", label: (a.textContent || symbol).trim().slice(0, 80), href: a.getAttribute("href") } : null;
    }
    function place(el, a) {
      const r = a.getBoundingClientRect();
      el.style.top = (window.scrollY + r.top + r.height / 2 - 9) + "px";
      el.style.left = (window.scrollX + r.right + 4) + "px";
    }
    function hide() { if (pop) { pop.remove(); pop = null; } }
    document.addEventListener("mouseover", e => {
      const a = e.target.closest && e.target.closest('a[href^="/t?symbol="]');
      if (!a || a.closest("#askdock") || a.closest("#listdrawer")) return;
      const n = nameOf(a); if (!n) return;
      if (!dot) {
        dot = document.createElement("button"); dot.type = "button"; dot.id = "rowdot"; dot.textContent = "⋯"; dot.title = "What to do with this name";
        dot.onclick = ev => { ev.preventDefault(); ev.stopPropagation(); openMenu(); };
        dot.addEventListener("mouseleave", () => { dot._t = setTimeout(() => { if (!pop) dot.style.display = "none"; }, 400); });
        dot.addEventListener("mouseenter", () => clearTimeout(dot._t));
        document.body.appendChild(dot);
      }
      cur = n; place(dot, a); dot.style.display = "block"; clearTimeout(dot._t);
      a.addEventListener("mouseleave", () => { dot._t = setTimeout(() => { if (!pop) dot.style.display = "none"; }, 400); }, { once: true });
    });
    document.addEventListener("click", e => { if (pop && !pop.contains(e.target) && e.target !== dot) hide(); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") hide(); });
    const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }).then(r => r.json());
    function item(label, fn) { const b = document.createElement("button"); b.type = "button"; b.textContent = label; b.onclick = ev => { ev.stopPropagation(); fn(b); }; return b; }
    function say(text) { railToast(text, "OK", () => {}); }
    async function openMenu() {
      hide();
      const n = cur; if (!n) return;
      pop = document.createElement("div"); pop.id = "rowmenu";
      const h = document.createElement("div"); h.className = "rm-h"; h.textContent = n.label + (n.label.toUpperCase() !== n.symbol ? " · " + n.symbol : ""); pop.appendChild(h);
      pop.appendChild(item("Open the name", () => { location.href = n.href; }));
      const watchLabel = { us: "Watch · US", global: "Global", home: "Watch · Home" }[n.region];
      const onThatList = location.pathname === "/watch" && ((new URLSearchParams(location.search).get("list") || "home") === n.region);
      if (!onThatList) pop.appendChild(item("Add to " + watchLabel, async b => {
        b.disabled = true; const out = await post("/api/watch/add", { code: n.symbol, list: n.region });
        say(out.ok ? `${n.symbol} is on ${watchLabel}.` : (out.error || "That did not work.")); if (out.journal && window.deskJournal) window.deskJournal(out.journal); hide();
      }));
      pop.appendChild(item("A note on it", () => { location.href = "/notes?new&symbol=" + encodeURIComponent(n.symbol); }));
      pop.appendChild(item("A task on it", b => {
        const t = prompt(`A task on ${n.symbol} (a line; add "by 2026-10-01" for a date)`); if (!t) return;
        const m = t.match(/\bby\s+(\d{4}-\d{2}-\d{2})\b/); const text = m ? t.replace(m[0], "").trim() : t.trim();
        post("/api/research/tasks/add", { text, symbol: n.symbol, due: m ? m[1] : "" }).then(out => { say(out.ok ? "Task saved. Open your tasks on Notes." : (out.error || "That did not save.")); hide(); });
      }));
      pop.appendChild(item("Put it on a chain", async b => {
        b.disabled = true;
        let d; try { d = await (await fetch("/api/chain", { cache: "no-store" })).json(); } catch (e) { say("The chains could not be read."); return; }
        const chains = (d.chains || []);
        const sub = document.createElement("div"); sub.className = "rm-sub";
        if (!chains.length) { sub.textContent = "No chain yet; make one on Chain first."; }
        chains.forEach(c => {
          const t = document.createElement("div"); t.className = "rm-chain"; t.textContent = c.title; sub.appendChild(t);
          (c.layers || []).forEach(l => sub.appendChild(item("  " + l.n + " · " + l.name, async () => {
            const chain = JSON.parse(JSON.stringify(c)); delete chain.starter;
            const layer = chain.layers.find(x => x.n === l.n);
            if (!layer.names.some(x => (x.code || "").toUpperCase() === n.symbol)) layer.names.push({ code: n.symbol, label: n.label.toUpperCase() === n.symbol ? n.symbol : n.label, region: n.region === chain.region ? "" : n.region, status: "CONTEXT", receipt: "REPORTED", note: "", source: "" });
            const out = await post("/api/chain/save", { chain });
            say(out.ok ? `${n.symbol} is on ${c.title}, layer ${l.n}.` : (out.error || "That did not save.")); if (out.journal && window.deskJournal) window.deskJournal(out.journal); hide();
          })));
        });
        b.replaceWith(sub);
      }));
      pop.appendChild(item("Ask SuperAnalyst about it", () => {
        hide(); openAsk(true);
        setTimeout(() => { const i = document.getElementById("askin"); if (i) { i.value = `What does this screen show for ${n.symbol}, and what would you look at next?`; i.focus(); } }, 250);
      }));
      document.body.appendChild(pop);
      place(pop, dot); pop.style.top = (parseFloat(dot.style.top) + 20) + "px"; pop.style.left = dot.style.left;
      const r = pop.getBoundingClientRect(); if (r.right > window.innerWidth - 8) pop.style.left = (window.scrollX + window.innerWidth - r.width - 12) + "px";
    }
  })();
  (function () {   // the reader's own lists: the drawer script, on every page
    if (document.querySelector('script[src="/assets/lists.js"]')) return;
    const sc = document.createElement("script"); sc.src = "/assets/lists.js"; sc.defer = true; document.head.appendChild(sc);
  })();
  /* ---- the journal's question: a moment the desk saw, held until the reader says.
     This time writes it; Always writes it and every one after without asking; Not now
     lets it go; Never switches the journal off. A decision (a status, a book change)
     gets a why box. Nothing is written until one of the four is pressed. ------- */
  let jtoastTimer = null;
  window.deskJournal = function (j) {
    if (!j || !j.pending) return;
    const e = j.pending;
    const old = document.getElementById("jtoast"); if (old) old.remove();
    const t = document.createElement("div");
    t.id = "jtoast";
    t.innerHTML = `<div class="jt"><b>Journal</b> ${esc((e.symbol ? "$" + e.symbol + " · " : "") + e.text)}</div>` +
      (e.decision ? `<input class="jw" placeholder="why? one line, or leave it" maxlength="500">` : "") +
      `<div class="jb"><button data-a="once">This time</button><button data-a="always">Always</button><button data-a="skip" class="ghost">Not now</button><button data-a="never" class="ghost">Never</button></div>`;
    document.body.appendChild(t);
    const done = () => t.remove();
    t.querySelectorAll("button").forEach(b => b.onclick = async () => {
      const a = b.dataset.a, why = (t.querySelector(".jw") || {}).value || "";
      t.querySelectorAll("button").forEach(x => x.disabled = true);
      try {
        if (a === "always" || a === "never") {
          await fetch("/api/settings/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ JOURNAL: a }) });
        }
        await fetch("/api/research/journal/decide", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: e.id, write: a === "once" || a === "always", why }) });
      } catch (err) { /* the moment stays held; the Notes screen lists it */ }
      done();
      if (a === "always") railToast("The journal now writes every moment on its own. Change it on Settings. ", "OK", () => {});
      if (a === "never") railToast("The journal is off. Switch it back on under Settings. ", "OK", () => {});
    });
    const w = t.querySelector(".jw");
    if (w) w.addEventListener("keydown", ev => { if (ev.key === "Enter") { ev.preventDefault(); t.querySelector('[data-a="once"]').click(); } });
    clearTimeout(jtoastTimer);
    jtoastTimer = setTimeout(() => { if (document.body.contains(t)) t.remove(); }, 60000);   // held, never dropped: the Notes screen still lists it
  };
  function applyNav(nav) {
    const next = new Set(nav.hidden || []);
    let same = next.size === hidden.size && [...next].every(k => hidden.has(k));
    hidden = next; store.setItem("desk_hidden", JSON.stringify([...hidden]));
    const ptabs = (nav.plugin_screens || []).map(p => [p.href, p.label, p.group || "Plugins", PLUG_ICON, p.key]);
    if (JSON.stringify(ptabs) !== JSON.stringify(PLUGIN_TABS)) { PLUGIN_TABS = ptabs; store.setItem("desk_plugin_tabs", JSON.stringify(ptabs)); same = false; }
    if (!same) buildRail();
    if (nav.journal_pending && !document.getElementById("jtoast") && location.pathname !== "/notes" && !sessionStorage.getItem("jseen")) {
      try { sessionStorage.setItem("jseen", "1"); } catch (e) { /* fine */ }
      railToast(`${nav.journal_pending} moment${nav.journal_pending === 1 ? "" : "s"} waiting for your journal. `, "Review", () => { location.href = "/notes?journal"; });
    }
    window.deskNav = nav;
    window.dispatchEvent(new CustomEvent("desk:nav", { detail: nav }));
  }
  async function refreshNav() {
    try { const r = await fetch("/api/nav"); if (r.ok) applyNav(await r.json()); } catch (e) { /* keep the browser copy */ }
  }
  window.deskRefreshNav = refreshNav;
  function syncFoot() {
    const t = document.getElementById("themename");
    if (t) t.textContent = document.documentElement.dataset.theme || "graphite";
    const min = document.documentElement.dataset.rail === "min";
    const g = document.getElementById("railglyph");
    if (g) g.textContent = min ? "⟩" : "⟨";
    const e = document.getElementById("railedge");
    if (e) e.textContent = min ? "›" : "‹";
    const b = document.getElementById("railbtn");
    if (b) {
      const lbl = b.querySelector("span:last-child");
      if (lbl) lbl.textContent = min ? "Expand" : "Collapse";
    }
  }
  function toggleRail() {
    const next = document.documentElement.dataset.rail === "min" ? "full" : "min";
    document.documentElement.dataset.rail = next;
    store.setItem("desk_rail", next);
    syncFoot();
    window.dispatchEvent(new Event("resize"));   // charts re-measure their width
  }

  /* ---- command palette: pages + live ticker search ----------------------- */
  let ckOpen = false, ckSel = 0, ckItems = [], ckSeq = 0;
  function buildCmdk() {
    if (document.getElementById("cmdk")) return;
    const el = document.createElement("div");
    el.id = "cmdk";
    el.innerHTML = '<div class="ck"><input placeholder="Jump to a page, type a ticker, or search your notes and files…" ' +
      'spellcheck="false" autocomplete="off"><div class="ckr"></div></div>';
    document.body.appendChild(el);
    el.addEventListener("mousedown", e => { if (e.target === el) openCmdk(false); });
    const inp = el.querySelector("input");
    inp.addEventListener("input", () => queueSearch(inp.value));
    inp.addEventListener("keydown", e => {
      if (e.key === "ArrowDown") { e.preventDefault(); moveSel(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); moveSel(-1); }
      else if (e.key === "Enter") { e.preventDefault(); go(ckItems[ckSel]); }
      else if (e.key === "Escape") openCmdk(false);
    });
  }
  function openCmdk(open) {
    buildCmdk();
    ckOpen = open;
    const el = document.getElementById("cmdk");
    el.classList.toggle("open", open);
    if (open) {
      const inp = el.querySelector("input");
      inp.value = ""; inp.focus();
      renderCk({ pages: allTabs().map(([href, label]) => ({ href, label })).concat([{ href: "#guide", label: "The startup guide" }]), us: [], in: [] });
    }
  }
  function go(item) {
    if (!item) return;
    if (item.href === "#guide") { openCmdk(false); window.deskGuide.show(); return; }
    location.href = item.href;
  }
  function moveSel(d) {
    if (!ckItems.length) return;
    ckSel = (ckSel + d + ckItems.length) % ckItems.length;
    document.querySelectorAll("#cmdk .cki").forEach((n, i) =>
      n.classList.toggle("sel", i === ckSel));
  }
  let ckTimer = null;
  function queueSearch(q) {
    clearTimeout(ckTimer);
    ckTimer = setTimeout(() => runSearch(q.trim()), 200);
  }
  async function runSearch(q) {
    const seq = ++ckSeq;
    const pages = allTabs().filter(([, label]) =>
      !q || label.toLowerCase().includes(q.toLowerCase()))
      .map(([href, label]) => ({ href, label }));
    if (q.length < 2) { renderCk({ pages, us: [], in: [], notes: [] }); return; }
    let us = [], ind = [], notes = [];
    try {
      const [ru, ri, rn] = await Promise.all([
        fetch("/api/search?q=" + encodeURIComponent(q) + "&list=us").then(r => r.json()),
        fetch("/api/search?q=" + encodeURIComponent(q) + "&list=home").then(r => r.json()),
        fetch("/api/notes?q=" + encodeURIComponent(q)).then(r => r.json()),
      ]);
      us = (ru.results || []).slice(0, 5);
      ind = (ri.results || []).slice(0, 5);
      notes = (rn.notes || []).slice(0, 6);
    } catch (e) { /* offline page search still works */ }
    if (seq !== ckSeq || !ckOpen) return;
    renderCk({ pages, us, in: ind, notes });
  }
  function renderCk(d) {
    const r = document.querySelector("#cmdk .ckr");
    if (!r) return;
    ckItems = []; ckSel = 0;
    let html = "";
    const section = (title, rows) => {
      if (!rows.length) return;
      html += `<div class="ckh">${title}</div>`;
      for (const it of rows) {
        html += `<div class="cki" data-i="${ckItems.length}"><span class="nm">${it.nm}</span>` +
          (it.sub ? `<span>${it.sub}</span>` : "") +
          (it.ex ? `<span class="ex">${it.ex}</span>` : "") + "</div>";
        ckItems.push(it);
      }
    };
    section("Pages", d.pages.map(p => ({ nm: p.label, href: p.href, ex: "page" })));
    section("Tickers · US", d.us.map(t => ({
      nm: t.code, sub: t.name, ex: t.exch, href: "/t?symbol=" + encodeURIComponent(t.code) })));
    section("Tickers · Home", d.in.map(t => ({
      nm: t.code, sub: t.name, ex: t.exch,
      href: "/t?symbol=" + encodeURIComponent(t.code) + "&region=home" })));
    section("Your notes and files", (d.notes || []).map(n => ({
      nm: esc(n.title), sub: esc((n.hit === "file" ? "in the file · " : "") + (n.snippet || "")).slice(0, 140),
      ex: esc([n.type, n.period].filter(Boolean).join(" · ")), href: "/notes?id=" + encodeURIComponent(n.id) })));
    r.innerHTML = html || '<div class="ckempty">Nothing matches.</div>';
    r.querySelectorAll(".cki").forEach(n => {
      n.onclick = () => go(ckItems[+n.dataset.i]);
      n.onmousemove = () => { ckSel = +n.dataset.i;
        r.querySelectorAll(".cki").forEach((m, i) => m.classList.toggle("sel", i === ckSel)); };
    });
    const first = r.querySelector(".cki");
    if (first) first.classList.add("sel");
  }

  /* ---- global keys: ⌘K palette, [ rail toggle ---------------------------- */
  function typing(e) {
    const t = e.target;
    return t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
  }
  document.addEventListener("keydown", e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault(); openCmdk(!ckOpen); return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "i") {
      e.preventDefault(); openAsk(!askOpen); return;
    }
    if (ckOpen && e.key === "Escape") { openCmdk(false); return; }
    if (askOpen && e.key === "Escape") { openAsk(false); return; }
    if (e.key === "[" && !typing(e) && !e.metaKey && !e.ctrlKey) toggleRail();
  });

  /* ---- bottom alert bar --------------------------------------------------
     Any page carrying <div id="alertbar"></div> gets the shared alert strip:
     a slim fixed bar at the bottom (count + latest), click to expand the
     full deduped list. */
  function initAlertBar() {
    const root = document.getElementById("alertbar");
    if (!root) return;
    root.innerHTML =
      '<div class="apanel"></div>' +
      '<div class="abar"><span class="acnt mono">0</span>' +
      '<span class="alatest"><span class="adot"></span><span class="txt"></span></span>' +
      '<span class="achev">alerts ▴</span></div>';
    const bar = root.querySelector(".abar");
    const panel = root.querySelector(".apanel");
    const chev = root.querySelector(".achev");
    let open = false;
    bar.onclick = () => {
      open = !open;
      panel.style.display = open ? "block" : "none";
      chev.textContent = open ? "hide ▾" : "alerts ▴";
    };
    async function pull() {
      try {
        const r = await fetch("/api/alerts");
        if (!r.ok) return;
        const d = await r.json();
        const seen = new Set(), rows = [];
        for (const a of d.active || []) {
          if (seen.has(a.text)) continue;
          seen.add(a.text);
          rows.push(a);
        }
        if (!rows.length) { root.style.display = "none"; return; }
        root.style.display = "block";
        if (!document.body.dataset.padded) {
          document.body.style.paddingBottom =
            (parseInt(getComputedStyle(document.body).paddingBottom) || 0) + 44 + "px";
          document.body.dataset.padded = "1";
        }
        const today = new Date().toLocaleDateString("sv-SE");
        const hot = rows.some(a => a.level === "hot");
        const cnt = root.querySelector(".acnt");
        cnt.textContent = rows.length;
        cnt.className = "acnt mono" + (hot ? " hot" : "");
        root.querySelector(".alatest .adot").className = "adot " + (rows[0].level || "");
        root.querySelector(".alatest .txt").textContent = rows[0].text;
        panel.innerHTML = rows.map(a => {
          const when = (a.date && a.date !== today) ? a.date.slice(5) + " " + a.ts : a.ts;
          return `<div class="arow"><span class="adot ${a.level || ""}"></span>` +
                 `<span class="txt">${a.text}</span><span class="atime mono">${when}</span></div>`;
        }).join("");
      } catch (e) { /* bar just stays as-is */ }
    }
    pull();
    setInterval(pull, 60000);
  }

  /* ---- update banner ------------------------------------------------------
     The desk looks at GitHub once a day (server side). When a newer version
     exists, this strip appears at the top of every page with the date and what
     changed, and one button. After an update the same strip says what was
     brought in and which files were kept because they were changed here. */
  function longDate(v) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(v || "");
    if (!m) return v || "";
    return new Date(+m[1], +m[2] - 1, +m[3], 12).toLocaleDateString("en-GB",
      { day: "numeric", month: "long", year: "numeric" });
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, c =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }
  function updateBar() {
    let el = document.getElementById("updatebar");
    if (!el) {
      el = document.createElement("div");
      el.id = "updatebar";
      document.body.prepend(el);
    }
    return el;
  }
  function keptHtml(kept) {
    if (!kept || !kept.length) return "";
    return `<div class="ukept">Kept as yours, because they were changed on this computer: ` +
      `<b>${kept.map(esc).join(", ")}</b>. Ask your agent to merge the new version's changes into them.</div>`;
  }
  let lastBoot = null;
  function migratedHtml(mg) {
    /* a release changed the shape of a file the reader owns: say which, and where the copy from before is */
    if (!mg) return "";
    const rows = [];
    for (const m of mg.migrated || []) rows.push(m.note
      ? `<b>${esc(m.label)}</b> was ${esc(m.note)}; the copy from before is at <span class="mono">${esc(m.kept.replace(/^.*cache\//, "cache/"))}</span>`
      : `<b>${esc(m.label)}</b> (${esc(m.path.split("/").slice(-2).join("/"))}) was brought up to this version's shape; the copy from before is at <span class="mono">${esc(m.kept.replace(/^.*cache\//, "cache/"))}</span>`);
    for (const n of mg.newer || []) rows.push(`<b>${esc(n.label)}</b> (${esc(n.path.split("/").slice(-2).join("/"))}) was written by a newer desk and is left as it is; update this desk to read it fully`);
    for (const e of mg.errors || []) rows.push(`could not bring one file up: ${esc(e)}`);
    return rows.length ? `<div class="ukept">${rows.join("<br>")}</div>` : "";
  }
  let deskVersion = "";
  function renderUpdate(st) {
    if (st.started) lastBoot = st.started;
    const el = updateBar();
    const c = st.check || {};
    deskVersion = c.local || st.local || deskVersion;
    const res = st.last_result;
    const dismissedAvail = store.getItem("desk_update_dismissed");
    const dismissedDone = store.getItem("desk_update_seen");
    const mg = st.migrations;
    if (mg && mg.at && store.getItem("desk_migration_seen") !== String(mg.at) && !(res && res.ok && res.to && (!c.local || c.local === res.to) && dismissedDone !== res.to)) {
      el.className = "done";
      el.innerHTML = `<div class="uin"><span class="utag">Your files</span><span class="utxt">This version changed the shape of a file you own. Nothing was lost.</span>` +
        `<button class="ubtn ghost" id="umok">OK</button></div>${migratedHtml(mg)}`;
      el.style.display = "block";
      document.getElementById("umok").onclick = () => { store.setItem("desk_migration_seen", String(mg.at)); el.style.display = "none"; };
      return;
    }
    // the Updated strip belongs to the version now running: a browser that never
    // saw an old update's strip is not shown it weeks later on a newer desk
    const fresh = res && res.ok && res.to && (!c.local || c.local === res.to) && (!res.at || Date.now() / 1000 - res.at < 7 * 86400);
    if (fresh && dismissedDone !== res.to) {
      el.className = "done";
      el.innerHTML = `<div class="uin"><span class="utag">Updated</span>` +
        `<span class="utxt">The desk was brought up to the <b>${esc(longDate(res.to))}</b> version` +
        (res.added_data && res.added_data.length ? `, with ${res.added_data.length} new data file${res.added_data.length > 1 ? "s" : ""}` : "") +
        (res.added_rules ? ` and ${res.added_rules} new alert rule${res.added_rules > 1 ? "s" : ""}` : "") +
        `.${res.pip && res.pip.indexOf("failed") === 0 ? " One dependency did not install; give your agent the file logs/desk-service.log." : ""}</span>` +
        `<button class="ubtn ghost" id="uok">OK</button></div>${keptHtml(res.kept)}${migratedHtml(mg)}`;
      el.style.display = "block";
      document.getElementById("uok").onclick = () => { store.setItem("desk_update_seen", res.to); if (mg && mg.at) store.setItem("desk_migration_seen", String(mg.at)); el.style.display = "none"; };
      return;
    }
    if (c.available && c.remote && dismissedAvail !== c.remote) {
      el.className = "avail";
      const what = (c.notes || []).map(n => esc(n.notes)).filter(Boolean);
      el.innerHTML = `<div class="uin"><span class="utag">Newer version</span>` +
        `<span class="utxt">A newer version of the desk is available, <b>${esc(longDate(c.remote))}</b>` +
        (what.length ? `: ${what[0]}` : "") + `.` +
        (what.length > 1 ? ` <span class="umore" title="${what.slice(1).join(" · ")}">and ${what.length - 1} earlier release${what.length > 2 ? "s" : ""}</span>` : "") +
        ` Your keys, your lists and any file your agent changed stay as they are.</span>` +
        `<button class="ubtn" id="ugo">Update the desk</button>` +
        `<button class="ubtn ghost" id="unot">Not now</button></div>`;
      el.style.display = "block";
      document.getElementById("unot").onclick = () => { store.setItem("desk_update_dismissed", c.remote); el.style.display = "none"; };
      document.getElementById("ugo").onclick = runUpdate;
      return;
    }
    el.style.display = "none";
  }
  async function runUpdate() {
    const el = updateBar();
    el.className = "busy";
    el.innerHTML = `<div class="uin"><span class="utag">Updating</span>` +
      `<span class="utxt">Bringing the newer version in. The desk restarts by itself when it is done, and this page reconnects on its own.</span></div>`;
    try {
      const r = await fetch("/api/update/apply", { method: "POST",
        headers: { "Content-Type": "application/json" }, body: "{}" });
      const rep = await r.json();
      if (!rep.ok) {
        el.className = "fail";
        el.innerHTML = `<div class="uin"><span class="utag">Not updated</span>` +
          `<span class="utxt">The update did not go through: ${esc(rep.error || "unknown reason")}. ` +
          `Nothing was changed. The other way is in the README under "Getting a newer version".</span>` +
          `<button class="ubtn ghost" id="uclose">Close</button></div>`;
        document.getElementById("uclose").onclick = () => { el.style.display = "none"; };
        return;
      }
      store.removeItem("desk_update_seen");
      el.className = "done";
      el.innerHTML = `<div class="uin"><span class="utag">Updated</span>` +
        `<span class="utxt">Updated to version <b>${esc(rep.to)}</b> (${esc(longDate(rep.to))}) in ${esc(rep.seconds)} seconds. ` +
        `The desk is restarting and this page reloads by itself in a moment.</span></div>` + keptHtml(rep.kept);
      waitForRestart(el, rep.folder);
    } catch (e) {
      /* the restart can cut the reply short; wait for the new start the same way */
      el.innerHTML = `<div class="uin"><span class="utag">Updated</span>` +
        `<span class="utxt">The desk is restarting and this page reloads by itself in a moment.</span></div>`;
      waitForRestart(el, null);
    }
  }
  /* After an update the process replaces itself in under a second, faster than the
     heartbeat below can notice, so watch the boot stamp instead and reload on change. */
  function waitForRestart(el, folder) {
    const t0 = Date.now();
    const tick = () => {
      fetch("/api/update", { cache: "no-store" }).then(r => r.json()).then(st => {
        if (st.started && lastBoot && st.started !== lastBoot) { location.reload(); return; }
        if (st.started && !lastBoot) { location.reload(); return; }
        if (Date.now() - t0 > 90000) { showRestartHelp(el, folder); return; }
        setTimeout(tick, 2000);
      }).catch(() => {
        if (Date.now() - t0 > 90000) { showRestartHelp(el, folder); return; }
        setTimeout(tick, 2000);
      });
    };
    setTimeout(tick, 1500);
  }
  function showRestartHelp(el, folder) {
    const where = folder ? `open the folder <b>${esc(folder)}</b>` : "open the desk's folder";
    el.className = "fail";
    el.innerHTML = `<div class="uin"><span class="utag">Not back yet</span>` +
      `<span class="utxt">The desk has not answered since the update. To start it by hand, ${where} and double-click <b>Start Desk</b>; ` +
      `if that does not bring it back, give the file logs/desk-service.log in that folder to your AI agent.</span></div>`;
  }
  function initUpdateBar() {
    async function pull() {
      try {
        const r = await fetch("/api/update", { cache: "no-store" });
        if (!r.ok) return;
        renderUpdate(await r.json());
      } catch (e) { /* offline: no banner */ }
    }
    pull();
    setInterval(pull, 30 * 60 * 1000);
  }

  /* ---- the Ask box: the reader's question, with this screen's numbers, to the
     AI they set in Settings. Reads the desk; writes nothing. ------------------- */
  let askOpen = false, askBusy = false, askDoors = [], askSt = {};
  // the conversation in the box: kept on this desk (not the vault) so closing the box, changing
  // screens or reloading brings it back; New starts another, the picker reopens an old one
  let askThread = { id: "", title: "", screen: "", msgs: [] };
  let askAbort = null, askId = "";
  function askDoor() { try { return store.getItem("gs.door") || ""; } catch (e) { return ""; } }
  function askPage() {
    const p = location.pathname === "/index.html" ? "/" : location.pathname;
    const sp = new URLSearchParams(location.search);
    const query = {};
    for (const k of ["list", "symbol", "region"]) if (sp.get(k)) query[k] = sp.get(k);
    const hit = TABS.find(([href]) => href === current());
    const label = hit ? hit[1] : (p === "/t" ? "Ticker " + (sp.get("symbol") || "") : document.title);
    return { page: p, query, label };
  }
  // The feedback loop: a broker the desk does not know, a market row that is
  // wrong, a screen that misreads. Every ticket opens prefilled on the desk's
  // public tracker with the screen and the version, and nothing is sent until
  // the reader presses the button there.
  const TRACKER = "https://gitlab.com/shikshan-nivesh/greeksoup/-/issues/new";
  function feedbackUrl(title, body) {
    const where = (askPage().label || document.title) + (deskVersion ? " · " + deskVersion : "");
    const t = title || ("On " + where);
    const b = (body || "What happened, and what you expected:\n\n") + "\n\nScreen: " + where;
    return TRACKER + "?issue[title]=" + encodeURIComponent(t) + "&issue[description]=" + encodeURIComponent(b);
  }
  window.deskFeedback = feedbackUrl;
  // another screen opens the box with a request ready: Settings hands a broker file to Build
  window.deskAsk = async (text, mode) => {
    await openAsk(true);
    const md = document.getElementById("askmode");
    if (mode && md && md.value !== mode) { md.value = mode; md.onchange(); }
    const ta = document.getElementById("askin");
    if (text) { ta.value = text; ta.focus(); }
  };
  function buildAsk() {
    if (document.getElementById("askdock")) return;
    const el = document.createElement("aside");
    el.id = "askdock";
    el.setAttribute("aria-label", "Ask SuperAnalyst");
    el.innerHTML =
      '<div class="agrip" title="Drag to set the width"></div>' +
      '<div class="ah"><div><b>SuperAnalyst</b><small id="asksub">an AI, reading this screen</small></div>' +
      '<button class="ax" id="askwide" title="Wider: a third, half, the whole screen, and back">' + svg(EXPAND_ICON) + '</button>' +
      '<button class="ax" id="askclose" title="Close (Esc)">' + svg(HIDE_ICON) + '</button>' +
      '<div class="arow"><select id="askvia" title="Who answers: an app you already pay for on this computer, or the key on Settings"></select>' +
      '<select id="askmodel" title="Which model answers. The first choice is the app\'s own default; the last lets you type a name the app accepts."></select>' +
      '<input id="askmodelin" placeholder="model name, as the app spells it" hidden></div>' +
      '<div class="arow"><select id="askmode" title="Research reads the desk and changes nothing. Build asks the app on this computer to change the desk itself.">' +
      '<option value="research">Research · reads the desk, changes nothing</option><option value="web">Research the web too · the desk first, then the web, with sources</option><option value="build">Build · changes this desk through the app above</option></select>' +
      '<select id="askthread" title="Your conversations, kept on this desk. Pick one to reopen it."></select>' +
      '<button class="ax at" id="asknew" title="New conversation">+</button>' +
      '<button class="ax at" id="askdel" title="Delete this conversation">' + svg(HIDE_ICON) + '</button></div></div>' +
      '<div class="am" id="askmsgs"></div>' +
      '<div class="af"><textarea id="askin" placeholder="Ask about what is on this screen. Enter sends, Shift+Enter for a new line."></textarea>' +
      '<div class="ab"><button id="asksend">Ask</button><small id="askfoot">SuperAnalyst is an AI reading this screen and the rest of the desk through the app or key you pick above. Verify against the source the screen names.</small></div></div>';
    document.body.appendChild(el);
    document.getElementById("askclose").onclick = () => openAsk(false);
    // the width is the reader's: drag the left edge, or step through a third, half and the
    // whole screen with the button; the last width is remembered
    const STEPS = [0.34, 0.5, 1];
    const minW = 360;
    let frac = 0.34;
    try { frac = parseFloat(store.getItem("ask_frac")) || 0.34; } catch (e) { /* fine */ }
    const apply = f => {
      frac = Math.min(1, Math.max(minW / window.innerWidth, f));
      el.style.width = frac >= 0.995 ? "100%" : Math.round(frac * window.innerWidth) + "px";
      el.classList.toggle("wide", frac >= 0.6);
      const wb = document.getElementById("askwide");
      wb.innerHTML = svg(frac >= 0.995 ? SHRINK_ICON : EXPAND_ICON);
      try { store.setItem("ask_frac", String(frac)); } catch (e) { /* fine */ }
    };
    apply(frac);
    document.getElementById("askwide").onclick = () => {
      const next = STEPS.find(s => s > frac + 0.02);
      apply(next === undefined ? STEPS[0] : next);
    };
    const grip = el.querySelector(".agrip");
    grip.addEventListener("mousedown", e => {
      e.preventDefault();
      const move = ev => apply((window.innerWidth - ev.clientX) / window.innerWidth);
      const up = () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); document.body.style.userSelect = ""; };
      document.body.style.userSelect = "none";
      window.addEventListener("mousemove", move); window.addEventListener("mouseup", up);
    });
    window.addEventListener("resize", () => apply(frac));
    // Research or Build: Build only through an app on this computer, and the box says so
    const mode = document.getElementById("askmode");
    try { mode.value = ["build", "web"].includes(store.getItem("ask_mode")) ? store.getItem("ask_mode") : "research"; } catch (e) { /* fine */ }
    mode.onchange = () => {
      try { store.setItem("ask_mode", mode.value); } catch (e) { /* fine */ }
      el.classList.toggle("build", mode.value === "build");
      const ta = document.getElementById("askin");
      ta.placeholder = mode.value === "build" ? "What to change on the desk. The app edits this desk's own files as you ask and says what it changed." : "Ask about what is on this screen. Enter sends, Shift+Enter for a new line.";
      if (mode.value === "web") {
        const via = document.getElementById("askvia");
        const d = askDoors.find(x => x.name === via.value);
        const can = d ? d.web : askSt.web;
        askNote(can ? `<p><b>Research the web too.</b> The desk's own screens go first, then ${d ? esc(d.label) : "the model"} searches the web for what they do not hold and cites every page it read. A figure it could not verify is said to be unverified. It takes longer.</p>`
                    : `<p><b>Research the web too</b> needs an app that can search: Claude Code, Codex or Gemini CLI on this computer, or an Anthropic key on Settings. ${d ? esc(d.label) + " cannot yet." : esc(askSt.web_why || "")} Pick one of those above, or Research, which reads the desk alone.</p>`, "hint");
      }
      if (mode.value === "build") {
        const via = document.getElementById("askvia");
        const d = askDoors.find(x => x.name === via.value);
        askNote(d ? (d.build ? `<p><b>Build.</b> ${esc(d.label)} will run in the desk's own folder and may change its files as you ask: a column, a screen, a plugin, a chain. It says what it changed when done; a change to the desk's own code needs a restart. The book, the watchlists and the vault are yours and stay yours.</p>`
                            : `<p><b>Build</b> needs an app the desk can let edit files: Claude Code, Codex, Gemini CLI or Qwen Code. ${esc(d.label)} answers questions only.</p>`)
                      : `<p><b>Build</b> needs an app on this computer (Claude Code, Codex, Gemini CLI, Qwen Code); a key can only answer. Pick one above.</p>`, "hint");
      }
    };
    el.classList.toggle("build", mode.value === "build");
    // the model: the app's own default first, then the names it accepts, then one typed
    const ms = document.getElementById("askmodel"), mi = document.getElementById("askmodelin");
    ms.onchange = () => {
      mi.hidden = ms.value !== "__type";
      if (ms.value === "__type") { mi.focus(); return; }
      try { store.setItem("gs.model." + askModelKey(), ms.value); } catch (e) { /* fine */ }
    };
    mi.onchange = () => { try { store.setItem("gs.model." + askModelKey(), "__type:" + mi.value.trim()); } catch (e) { /* fine */ } };
    // the conversations: pick one, start one, delete one
    document.getElementById("askthread").onchange = e => {
      const v = e.target.value;
      if (v === "__all") { askDeleteAll(); return; }
      askLoadThread(v);
    };
    document.getElementById("asknew").onclick = () => { if (askBusy) stopAsk(); askNewThread(true); };
    document.getElementById("askdel").onclick = askDeleteThread;
    document.getElementById("asksend").onclick = () => askBusy ? stopAsk() : sendAsk();
    document.getElementById("askin").addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendAsk(); }
    });
  }
  function askModelKey() { return (document.getElementById("askvia") || {}).value || "key"; }
  function askModelValue() {
    const ms = document.getElementById("askmodel"), mi = document.getElementById("askmodelin");
    if (!ms) return "";
    return ms.value === "__type" ? mi.value.trim() : ms.value;
  }
  function fillModels() {
    const ms = document.getElementById("askmodel"), mi = document.getElementById("askmodelin");
    const via = document.getElementById("askvia").value;
    const d = askDoors.find(x => x.name === via);
    let list = [], head, canPick = true;
    if (d) {
      list = d.models || [];
      canPick = !!d.model_flag;
      head = canPick ? `${d.label} decides (its default)` : `${d.label} picks its own model`;
    } else {
      list = askSt.models || [];
      head = askSt.model ? `${askSt.model} (on Settings)` : "the model on Settings";
    }
    ms.innerHTML = `<option value="">${esc(head)}</option>` + list.map(([id, label]) => `<option value="${esc(id)}">${esc(label)}</option>`).join("") +
      (canPick ? `<option value="__type">Another model name…</option>` : "");
    ms.disabled = !canPick;
    let want = "";
    try { want = store.getItem("gs.model." + askModelKey()) || ""; } catch (e) { /* fine */ }
    if (want.startsWith("__type:")) { ms.value = "__type"; mi.value = want.slice(7); mi.hidden = false; }
    else { mi.hidden = true; ms.value = list.some(([id]) => id === want) ? want : ""; }
  }
  function askNote(html, cls) {
    const m = document.getElementById("askmsgs");
    const d = document.createElement("div");
    d.className = "a" + (cls ? " " + cls : "");
    d.innerHTML = html;
    m.appendChild(d); m.scrollTop = m.scrollHeight;
    return d;
  }
  function askIntro() {
    const st = askSt, via = document.getElementById("askvia");
    if (st.ready || askDoors.some(d => d.ready)) {
      const dd = askDoors.find(d => d.name === via.value);
      const who = dd ? `<b>${esc(dd.label)}</b> on this computer${dd.pays ? ", on " + esc(dd.pays) : ""}` : st.ready ? `<b>${esc(st.label || st.provider)}</b>, model <span class="mono">${esc(st.model)}</span>` : "the app you pick above";
      askNote(`<p>SuperAnalyst is an AI. Ask anything: this screen's numbers go first, then the screens the question leads to (a name you mention, the short interest, the 13F holders, the calendar, your notes), all to ${who}, and nowhere else. The pickers above choose who answers and which model; Research, Research the web too, or Build, what it may read and what it may change. Every conversation is kept on this desk until you delete it. An answer worth keeping has a Save as note button under it.</p>`, "hint");
    } else {
      askNote(`<p>SuperAnalyst is an AI, and nothing answers for it yet. ${esc(st.why || "")} Three ways: sign in to an app you already pay for (the greyed names in the picker above; <a href="/settings">Settings</a>, under Your AI, opens the sign-in), paste a key from any lab there, or run a model on this computer, which needs no key.</p>`, "hint");
    }
  }
  function askRenderAnswer(box, msg) {
    // links in the answer open as links (the web mode cites its pages that way)
    // an app answers in light markdown: [title](url) and **bold** are the two shapes worth honouring
    const linkify = t => esc(t)
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (m, a, u) => `<a href="${u}" target="_blank" rel="noopener">${a}</a>`)
      .replace(/(^|[\s(])(https?:\/\/[^\s<)\]]+)/g, (m, pre, u) => `${pre}<a href="${u}" target="_blank" rel="noopener">${u}</a>`)
      .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
    box.innerHTML = msg.content.split(/\n{2,}/).map(p => `<p>${linkify(p).replace(/\n/g, "<br>")}</p>`).join("") +
      (msg.sources && msg.sources.length ? `<div class="rd">sources: ${msg.sources.map(x => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title || x.url)}</a>`).join(" · ")}</div>` : "") +
      (msg.read && msg.read.length ? `<div class="rd">read ${msg.read.map(esc).join(" · ")} · ${esc(msg.model || "")}</div>` : "");
  }
  function askRenderThread() {
    const m = document.getElementById("askmsgs");
    m.innerHTML = "";
    askIntro();
    const { query, label } = askPage();
    let lastQ = "";
    for (const msg of askThread.msgs) {
      if (msg.role === "user") {
        lastQ = msg.content;
        const qd = document.createElement("div"); qd.className = "q"; qd.textContent = msg.content; m.appendChild(qd);
      } else {
        const box = askNote("");
        askRenderAnswer(box, msg);
        offerSave(box, lastQ, { answer: msg.content, model: msg.model, read: msg.read }, query, label);
      }
    }
    m.scrollTop = m.scrollHeight;
  }
  async function askRefreshThreads() {
    const sel = document.getElementById("askthread");
    let rows = [];
    try { rows = (await (await fetch("/api/ask/threads", { cache: "no-store" })).json()).threads || []; } catch (e) { /* the box works without the list */ }
    const cur = askThread.id;
    const opts = [];
    if (!cur) opts.push(`<option value="">New conversation</option>`);
    for (const r of rows) opts.push(`<option value="${esc(r.id)}"${r.id === cur ? " selected" : ""}>${esc(r.title || "(untitled)")} · ${esc(r.at.slice(5, 16))}</option>`);
    if (rows.length) opts.push(`<option value="__all">Delete every conversation…</option>`);
    sel.innerHTML = opts.join("");
    if (cur) sel.value = cur;
    return rows;
  }
  async function askLoadThread(id) {
    if (askBusy) stopAsk();
    if (!id) { askNewThread(false); return; }
    try {
      const t = (await (await fetch("/api/ask/thread?id=" + encodeURIComponent(id), { cache: "no-store" })).json()).thread;
      if (t) { askThread = { id: t.id, title: t.title, screen: t.screen, msgs: t.msgs || [] }; askRenderThread(); }
    } catch (e) { /* fine */ }
    askRefreshThreads();
  }
  function askNewThread(refresh) {
    askThread = { id: "", title: "", screen: "", msgs: [] };
    askRenderThread();
    if (refresh) askRefreshThreads();
    document.getElementById("askin").focus();
  }
  async function askSaveThread() {
    if (!askThread.msgs.length) return;
    try {
      const r = await (await fetch("/api/ask/thread/save", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: askThread.id, title: askThread.title, screen: askThread.screen, msgs: askThread.msgs }) })).json();
      if (r.ok && r.thread) askThread.id = r.thread.id;
    } catch (e) { /* the thread lives in the box until the desk answers again */ }
    askRefreshThreads();
  }
  async function askDeleteThread() {
    if (askBusy) stopAsk();
    if (askThread.id) {
      try { await fetch("/api/ask/thread/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: askThread.id }) }); } catch (e) { /* fine */ }
    }
    askNewThread(true);
  }
  async function askDeleteAll() {
    if (!window.confirm("Delete every conversation kept on this desk?")) { askRefreshThreads(); return; }
    if (askBusy) stopAsk();
    try { await fetch("/api/ask/thread/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: "all" }) }); } catch (e) { /* fine */ }
    askNewThread(true);
  }
  async function openAsk(open) {
    buildAsk();
    askOpen = open;
    document.getElementById("askdock").classList.toggle("open", open);
    if (!open) return;
    const { label } = askPage();
    document.getElementById("asksub").textContent = "an AI, reading " + label;
    const m = document.getElementById("askmsgs");
    try {
      const st = await (await fetch("/api/ask", { cache: "no-store" })).json();
      askSt = st;
      askDoors = st.doors || [];
      // who answers, always in view: the key on Settings first, then every app the desk can
      // hand a question to, the ones not on this computer greyed so the reader sees what
      // else could answer and what a sign-in would add
      const via = document.getElementById("askvia");
      via.innerHTML = `<option value="">${esc(st.ready ? (st.label || st.provider) + " · key on Settings" : "A key on Settings (none yet)")}</option>` +
        askDoors.map(d => `<option value="${esc(d.name)}"${d.ready ? "" : " disabled"}>${esc(d.label)}${d.ready ? (d.pays ? " · " + esc(d.pays) : "") : " · not on this computer"}</option>`).join("");
      const want = askDoor() || st.default_door || "";     // the reader's last pick, else the app chosen on Settings
      if (askDoors.some(d => d.name === want && d.ready)) via.value = want;
      else if (!st.ready) { const first = askDoors.find(d => d.ready); if (first) via.value = first.name; }
      via.onchange = () => { try { store.setItem("gs.door", via.value); } catch (e) { /* fine */ } fillModels(); };
      fillModels();
      if (!m.childElementCount) {
        // the latest conversation comes back on open; nothing kept means a fresh box
        const rows = await askRefreshThreads();
        if (rows.length && !askThread.id) await askLoadThread(rows[0].id);
        else askRenderThread();
      }
    } catch (e) { /* the send will say */ }
    document.getElementById("askin").focus();
  }
  function stopAsk() {
    if (!askBusy) return;
    const id = askId;
    try { fetch("/api/ask/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id }) }); } catch (e) { /* fine */ }
    if (askAbort) askAbort.abort();
  }
  async function sendAsk() {
    if (askBusy) return;
    const ta = document.getElementById("askin");
    const question = ta.value.trim();
    if (!question) return;
    const { page, query, label } = askPage();
    askBusy = true;
    const send = document.getElementById("asksend");
    send.textContent = "Stop"; send.classList.add("stop");
    ta.value = "";
    const qd = document.createElement("div"); qd.className = "q"; qd.textContent = question;
    const m = document.getElementById("askmsgs"); m.appendChild(qd);
    const building = (document.getElementById("askmode") || {}).value === "build";
    const webbing = (document.getElementById("askmode") || {}).value === "web";
    const wait = askNote(`<p class="wait">${building ? "Working on the desk. This can take a few minutes…" : "Reading " + esc(label) + " and the screens the question points at" + (webbing ? ", then the web" : "") + ", and asking…"} Stop ends it.</p>`);
    const history = askThread.msgs.map(x => ({ role: x.role, content: x.content })).slice(-6);
    askId = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    askAbort = new AbortController();
    if (!askThread.title) { askThread.title = question.replace(/\s+/g, " ").slice(0, 60); askThread.screen = label; }
    try {
      const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, signal: askAbort.signal,
        body: JSON.stringify({ question, page, query, history, id: askId, model: askModelValue(), door: (document.getElementById("askvia") || {}).value || "", mode: (document.getElementById("askmode") || {}).value || "research" }) });
      const out = await r.json();
      if (!out.ok) {
        wait.className = "a err";
        wait.innerHTML = `<p>${esc(out.error || "The model did not answer.")}` +
          (out.settings ? ` Set it on <a href="/settings">Settings</a>, under Your AI.` : "") + `</p>`;
      } else {
        const msg = { role: "assistant", content: out.answer, model: out.model || "", read: out.read || [], sources: out.sources || [] };
        askRenderAnswer(wait, msg);
        askThread.msgs.push({ role: "user", content: question }, msg);
        offerSave(wait, question, out, query, label);
        askSaveThread();
      }
    } catch (e) {
      wait.className = "a err";
      wait.innerHTML = e && e.name === "AbortError" ? "<p>Stopped.</p>" : "<p>The desk did not answer. Is it still running?</p>";
    }
    askBusy = false; askAbort = null; askId = "";
    send.textContent = "Ask"; send.classList.remove("stop");
    m.scrollTop = m.scrollHeight; ta.focus();
  }

  /* ---- Save as note: an answer is kept only when the reader says so. The card is
     filled from the screen (the name on a ticker page, commodity on Commodities,
     macro on Macro) and the reader sets the period; the file lands in the research vault, data/research. */
  const ASK_KIND = { "/t": "stock", "/commods": "commodity", "/macro": "macro", "/chain": "sector" };
  const KIND_LABEL = { stock: "Stock", commodity: "Commodity", sector: "Sector", macro: "Macro", general: "General" };
  const ABOUT_HINT = { commodity: "which commodity", sector: "which sector", macro: "which theme", general: "a subject, or leave empty" };
  function offerSave(box, question, out, query, screen) {
    const sv = document.createElement("div");
    sv.className = "sv";
    sv.innerHTML = `<button type="button" class="svb">Save as note</button> <button type="button" class="svb svt2">Save as task</button>`;
    box.appendChild(sv);
    sv.querySelector(".svb").onclick = () => saveForm(sv, question, out, query, screen);
    sv.querySelector(".svt2").onclick = () => taskForm(sv, question, out, query, screen);
  }
  /* Save as task: the reader names the thing to do and when; the task carries the name and
     where it came from, and lands in tasks.md with the rest */
  function taskForm(sv, question, out, query, screen) {
    const sym = (query.symbol || "").toUpperCase();
    const CATS = { results: "Results", filing: "Filing", "follow-up": "Follow-up", model: "Model", reading: "Reading", call: "Call", other: "Other" };
    sv.innerHTML =
      `<div class="svf"><input class="svt" placeholder="The task, in your words" value="${esc(question.replace(/\s+/g, " ").trim().slice(0, 120))}">` +
      `<div class="svr"><input class="svs" placeholder="symbol" value="${esc(sym)}" style="flex:0 0 90px;text-transform:uppercase"><input class="svp" type="date" title="due" style="width:auto">` +
      `<select class="svk">${Object.keys(CATS).map(k => `<option value="${k}"${k === "follow-up" ? " selected" : ""}>${CATS[k]}</option>`).join("")}</select></div>` +
      `<div class="svr"><button type="button" class="svgo">Save task</button><button type="button" class="svno">Cancel</button><small class="svm">Lands in your tasks with the screen it came from.</small></div></div>`;
    sv.querySelector(".svno").onclick = () => { const box = sv.parentNode; sv.remove(); offerSave(box, question, out, query, screen); };
    sv.querySelector(".svgo").onclick = async () => {
      const msg = sv.querySelector(".svm"), text = sv.querySelector(".svt").value.trim();
      if (!text) { msg.textContent = "Say what the task is first."; return; }
      sv.querySelector(".svgo").disabled = true;
      try {
        const r = await fetch("/api/research/tasks/add", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, symbol: sv.querySelector(".svs").value.trim(), due: sv.querySelector(".svp").value, category: sv.querySelector(".svk").value, source: "an answer on " + screen }) });
        const d = await r.json();
        if (!d.ok) throw new Error(d.error || "could not save");
        sv.innerHTML = `<small class="svm">Task saved. <a href="/notes?tasks">Open your tasks</a></small>`;
      } catch (e) { sv.querySelector(".svgo").disabled = false; msg.textContent = "Not saved: " + (e.message || "the desk did not answer."); }
    };
    sv.querySelector(".svt").focus();
  }
  function saveForm(sv, question, out, query, screen) {
    const page = askPage().page;
    const sym = (query.symbol || "").toUpperCase();
    const kind0 = ASK_KIND[page] || "general";
    let lastPeriod = "";
    try { lastPeriod = localStorage.getItem("gs.period") || ""; } catch (e) { /* private window */ }
    const title0 = question.replace(/\s+/g, " ").trim().slice(0, 90);
    sv.innerHTML =
      `<div class="svf">` +
      `<input class="svt" placeholder="Title" value="${esc(title0)}">` +
      `<div class="svr"><select class="svk" title="what the note is about">${Object.keys(KIND_LABEL).map(k => `<option value="${k}"${k === kind0 ? " selected" : ""}>${KIND_LABEL[k]}</option>`).join("")}</select>` +
      `<input class="svs" placeholder="symbols, comma separated" value="${esc(sym)}" title="the listings the note is about">` +
      `<input class="sva" placeholder="${esc(ABOUT_HINT[kind0] || "")}" title="the commodity, sector or theme">` +
      `<input class="svp" placeholder="Q2 FY26" value="${esc(lastPeriod)}" title="the quarter or year being researched"></div>` +
      `<div class="svr"><button type="button" class="svgo">Save</button><button type="button" class="svno">Cancel</button><small class="svm">Files the question and this answer in your research vault.</small></div></div>`;
    const k = sv.querySelector(".svk"), s = sv.querySelector(".svs"), a = sv.querySelector(".sva");
    const showKind = () => { const st = k.value === "stock"; s.hidden = !st; a.hidden = st; a.placeholder = ABOUT_HINT[k.value] || ""; };
    k.onchange = showKind; showKind();
    sv.querySelector(".svno").onclick = () => { const box = sv.parentNode; sv.remove(); offerSave(box, question, out, query, screen); };
    sv.querySelector(".svgo").onclick = async () => {
      const msg = sv.querySelector(".svm");
      const title = sv.querySelector(".svt").value.trim();
      if (!title) { msg.textContent = "A title first."; return; }
      const period = sv.querySelector(".svp").value.trim();
      const when = new Date();
      const stamp = when.getFullYear() + "-" + String(when.getMonth() + 1).padStart(2, "0") + "-" + String(when.getDate()).padStart(2, "0");
      const body = "> " + question.replace(/\n/g, "\n> ") + "\n\n" + out.answer.trim() + "\n\n" +
        `*Asked on ${screen}, ${stamp}; answered by ${out.model || "your AI"}. Verify against the source the screen names.*\n`;
      const note = { title, kind: k.value, type: "answer", period,
        symbols: k.value === "stock" ? s.value.split(",").map(x => x.trim().toUpperCase()).filter(Boolean) : [],
        about: k.value === "stock" ? "" : a.value.trim(), tags: ["ask"], body };
      sv.querySelector(".svgo").disabled = true; msg.textContent = "Saving…";
      try {
        const r = await fetch("/api/notes/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(note) });
        const d = await r.json();
        if (!d.ok) throw new Error(d.error || "could not save");
        try { if (d.note.period) localStorage.setItem("gs.period", d.note.period); } catch (e) { /* fine */ }
        sv.innerHTML = `<small class="svm">Saved. <a href="/notes?id=${encodeURIComponent(d.note.id)}">Open the note</a> · <span class="mono">${esc(d.note.path)}</span></small>`;
        window.deskJournal(d.journal);
      } catch (e) {
        sv.querySelector(".svgo").disabled = false; msg.textContent = "Not saved: " + (e.message || "the desk did not answer.");
      }
    };
    sv.querySelector(".svt").focus();
  }

  function boot() { buildRail(); refreshNav(); initAlertBar(); initUpdateBar(); }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  /* ---- heartbeat: if the desk restarts under an open page, say so and reload
     the page the moment it answers again ------------------------------------ */
  (function () {
    var fails = 0, wasDown = false, bar = null;
    function showBar() {
      if (bar) return;
      bar = document.createElement("div");
      bar.id = "desk-reconnect";
      bar.textContent = "The desk is restarting. This page reconnects by itself.";
      bar.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:9999;padding:8px 14px;background:#b8860b;color:#111;font:600 13px -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;text-align:center";
      document.body.appendChild(bar);
    }
    setInterval(function () {
      fetch("/api/ping", { cache: "no-store" }).then(function (r) {
        if (!r.ok) throw new Error("down");
        if (wasDown) { location.reload(); return; }
        fails = 0;
      }).catch(function () {
        fails++;
        if (fails >= 2) { wasDown = true; showBar(); }
      });
    }, 5000);
  })();
})();

/* ---- search-as-you-type on any add box --------------------------------------
   deskSuggest(input, {list, onPick}) hangs the desk's name search under an input:
   type two letters, the listings that match drop down (code, company, exchange),
   arrows and Enter pick one, a click picks one, Escape closes. The same box the
   Watch screens have, so Flow, Short and any screen that takes a name behave alike. */
(function () {
  const CSS = `.dsug{display:none;position:absolute;top:calc(100% + 4px);left:0;z-index:30;min-width:340px;max-width:460px;background:var(--panel);border:1px solid var(--line2);border-radius:10px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.5)}
.dsug .sg{display:flex;align-items:baseline;gap:10px;padding:8px 13px;cursor:pointer;border-bottom:1px solid var(--line);font-size:12.5px;text-transform:none}
.dsug .sg:last-child{border-bottom:none} .dsug .sg:hover,.dsug .sg.sel{background:var(--panel2)}
.dsug .c{font-weight:800;min-width:74px;font-family:var(--mono,ui-monospace,monospace)} .dsug .n{color:var(--ink2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap} .dsug .e{color:var(--muted);font-size:10px;white-space:nowrap}`;
  const EXN = { NSE: "NSE", BSE: "BSE", NASDAQ: "Nasdaq", NYSE: "NYSE", AMEX: "NYSE American", NMS: "Nasdaq", NYQ: "NYSE", NGM: "Nasdaq", NCM: "Nasdaq", PCX: "NYSE Arca", BATS: "Cboe" };
  window.deskSuggest = function (input, opts) {
    const o = opts || {};
    if (!document.getElementById("dsug-css")) { const st = document.createElement("style"); st.id = "dsug-css"; st.textContent = CSS; document.head.appendChild(st); }
    const wrap = input.parentElement;
    if (getComputedStyle(wrap).position === "static") wrap.style.position = "relative";
    const box = document.createElement("div"); box.className = "dsug"; wrap.appendChild(box);
    let timer = null, items = [], sel = -1;
    const hide = () => { box.style.display = "none"; items = []; sel = -1; };
    const paint = () => {
      if (!items.length) { hide(); return; }
      box.innerHTML = items.map((r, i) => `<div class="sg ${i === sel ? "sel" : ""}" data-i="${i}"><span class="c">${r.code}</span><span class="n">${r.name || ""}</span><span class="e">${EXN[(r.exch || "").toUpperCase()] || r.exch || ""}</span></div>`).join("");
      box.style.display = "block";
      box.querySelectorAll(".sg").forEach(el => { el.onmousedown = e => { e.preventDefault(); pick(+el.dataset.i); }; });
    };
    const pick = i => { const r = items[i]; if (!r) return; input.value = r.code; hide(); if (o.onPick) o.onPick(r); };
    input.addEventListener("input", () => {
      clearTimeout(timer); const q = input.value.trim(); if (q.length < 2) { hide(); return; }
      timer = setTimeout(async () => {
        try {
          const d = await (await fetch(`/api/search?q=${encodeURIComponent(q)}&list=${o.list || "us"}`)).json();
          if (input.value.trim() !== q) return;
          items = d.results || []; sel = -1; paint();
        } catch (e) { /* the box stays closed */ }
      }, 280);
    });
    input.addEventListener("blur", () => setTimeout(hide, 150));
    input.addEventListener("keydown", e => {
      if (box.style.display !== "block") return;
      if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(items.length - 1, sel + 1); paint(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); paint(); }
      else if (e.key === "Escape") { hide(); }
      else if (e.key === "Enter" && sel >= 0) { e.preventDefault(); pick(sel); }
    });
    return { hide };
  };
})();

/* ---- the time axis every history chart shares ------------------------------
   A series the desk keeps is often denser at the near end (daily for the last
   two years, weekly before, monthly before that), so a chart that spaces points
   by index stretches the recent years across most of the width and squeezes
   the old ones into a sliver. Every big chart places a point by its DATE:
   deskTimeScale gives the x for a date, and deskTimeTicks the year or month
   boundaries to label, so 2019 and 2025 are the same width on the axis. */
(function () {
  "use strict";
  const YEAR = 31557600000;
  /* dates: the series' "YYYY-MM-DD" strings, ascending. Returns {T, x(i), at(t)}:
     T the parsed times, x(i) the pixel for point i, at(t) the nearest index to a time. */
  window.deskTimeScale = function (dates, left, width) {
    const T = dates.map(d => Date.parse(d));
    const t0 = T[0], span = (T[T.length - 1] - t0) || 1;
    const xOf = t => left + ((t - t0) / span) * width;
    return {
      T, t0, t1: T[T.length - 1],
      x: i => xOf(T[i]),
      xt: xOf,
      t: px => t0 + ((px - left) / width) * span,
      at: t => {                       // nearest point to a time, by binary search
        let lo = 0, hi = T.length - 1;
        while (lo < hi) { const mid = (lo + hi) >> 1; if (T[mid] < t) lo = mid + 1; else hi = mid; }
        return lo > 0 && (t - T[lo - 1]) < (T[lo] - t) ? lo - 1 : lo;
      },
    };
  };
  /* [[time, label], ...] at year boundaries when the span is long, month
     boundaries when it is short; never more than nMax labels. */
  window.deskTimeTicks = function (t0, t1, nMax) {
    nMax = nMax || 7;
    const out = [], yrs = (t1 - t0) / YEAR, a = new Date(t0);
    if (yrs >= 2.5) {
      const need = Math.max(1, Math.floor(yrs / nMax));
      const s = [1, 2, 3, 5, 10, 20, 50].find(v => v >= need) || 50;
      const y1 = new Date(t1).getUTCFullYear();
      for (let y = Math.ceil(a.getUTCFullYear() / s) * s; y <= y1; y += s) {
        const t = Date.UTC(y, 0, 1);
        if (t >= t0 && t <= t1) out.push([t, String(y)]);
      }
    } else {
      const months = yrs * 12, s = months <= 7 ? 1 : (months <= 14 ? 2 : (months <= 21 ? 3 : 6));
      let y = a.getUTCFullYear(), m = a.getUTCMonth() + 1;
      if (m > 11) { m = 0; y++; }
      for (let k = 0; k < 400; k++) {
        const t = Date.UTC(y, m, 1);
        if (t > t1) break;
        if (m % s === 0) out.push([t, y + "-" + String(m + 1).padStart(2, "0")]);
        m++; if (m > 11) { m = 0; y++; }
      }
    }
    return out;
  };
})();
