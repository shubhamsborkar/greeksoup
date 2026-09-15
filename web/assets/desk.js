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
    ["/", "Desk · Home", "Desks", I.deskin, "home"],
    ["/usdesk", "Desk · US", "Desks", I.deskus, "usdesk"],
    ["/book", "Desk · Book", "Desks", I.book, "book"],
    ["/risk", "Risk", "Desks", I.risk, "risk"],
    ["/watch", "Watch · Home", "Watchlists", I.watch, "watch"],
    ["/watch?list=us", "Watch · US", "Watchlists", I.list, "watchus"],
    ["/watch?list=global", "Global", "Watchlists", I.globe, "global"],
    ["/funds", "Funds", "Intelligence", I.funds, "funds"],
    ["/flow", "Flow", "Intelligence", I.flow, "flow"],
    ["/short", "Short", "Intelligence", I.short, "short"],
    ["/capitol", "Capitol", "Intelligence", I.capitol, "capitol"],
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
      '<button id="askbtn" title="Ask your AI about this screen (⌘I)"><span class="rk">✦</span><span>Ask · your AI</span></button>' +
      '<button id="cmdkbtn" title="Jump anywhere (⌘K)"><span class="rk">⌘</span><span>Command · K</span></button>' +
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
      renderCk({ pages: allTabs().map(([href, label]) => ({ href, label })), us: [], in: [] });
    }
  }
  function go(item) {
    if (item) location.href = item.href;
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
  function renderUpdate(st) {
    if (st.started) lastBoot = st.started;
    const el = updateBar();
    const c = st.check || {};
    const res = st.last_result;
    const dismissedAvail = store.getItem("desk_update_dismissed");
    const dismissedDone = store.getItem("desk_update_seen");
    if (res && res.ok && res.to && dismissedDone !== res.to) {
      el.className = "done";
      el.innerHTML = `<div class="uin"><span class="utag">Updated</span>` +
        `<span class="utxt">The desk was brought up to the <b>${esc(longDate(res.to))}</b> version` +
        (res.added_data && res.added_data.length ? `, with ${res.added_data.length} new data file${res.added_data.length > 1 ? "s" : ""}` : "") +
        (res.added_rules ? ` and ${res.added_rules} new alert rule${res.added_rules > 1 ? "s" : ""}` : "") +
        `.${res.pip && res.pip.indexOf("failed") === 0 ? " One dependency did not install; give your agent the file logs/desk-service.log." : ""}</span>` +
        `<button class="ubtn ghost" id="uok">OK</button></div>${keptHtml(res.kept)}`;
      el.style.display = "block";
      document.getElementById("uok").onclick = () => { store.setItem("desk_update_seen", res.to); el.style.display = "none"; };
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
  let askOpen = false, askBusy = false, askDoors = [];
  const askHistory = [];
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
  function buildAsk() {
    if (document.getElementById("askdock")) return;
    const el = document.createElement("aside");
    el.id = "askdock";
    el.setAttribute("aria-label", "Ask your AI");
    el.innerHTML =
      '<div class="ah"><div><b>Ask your AI</b><small id="asksub">reading this screen</small></div>' +
      '<select id="askvia" title="who answers: the AI on Settings, or a door a plugin opened" hidden></select>' +
      '<button class="ax" id="askclose" title="Close (Esc)">×</button></div>' +
      '<div class="am" id="askmsgs"></div>' +
      '<div class="af"><textarea id="askin" placeholder="Ask about what is on this screen. Enter sends, Shift+Enter for a new line."></textarea>' +
      '<div class="ab"><button id="asksend">Ask</button><small id="askfoot">Your AI, reading this screen. Verify against the source the screen names.</small></div></div>';
    document.body.appendChild(el);
    document.getElementById("askclose").onclick = () => openAsk(false);
    document.getElementById("asksend").onclick = sendAsk;
    document.getElementById("askin").addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendAsk(); }
    });
  }
  function askNote(html, cls) {
    const m = document.getElementById("askmsgs");
    const d = document.createElement("div");
    d.className = "a" + (cls ? " " + cls : "");
    d.innerHTML = html;
    m.appendChild(d); m.scrollTop = m.scrollHeight;
    return d;
  }
  async function openAsk(open) {
    buildAsk();
    askOpen = open;
    document.getElementById("askdock").classList.toggle("open", open);
    if (!open) return;
    const { label } = askPage();
    document.getElementById("asksub").textContent = "reading " + label;
    const m = document.getElementById("askmsgs");
    try {
      const st = await (await fetch("/api/ask", { cache: "no-store" })).json();
      askDoors = st.doors || [];
      const via = document.getElementById("askvia");
      if (askDoors.length) {
        via.hidden = false;
        via.innerHTML = `<option value="">${esc(st.ready ? (st.label || st.provider) + " (Settings)" : "Your AI (not set)")}</option>` +
          askDoors.map(d => `<option value="${esc(d.name)}"${d.ready ? "" : " disabled"}>${esc(d.label)}${d.via ? " · " + esc(d.via) : d.ready ? "" : " (not found)"}</option>`).join("");
        const want = askDoor();
        if (askDoors.some(d => d.name === want && d.ready)) via.value = want;
        via.onchange = () => { try { store.setItem("gs.door", via.value); } catch (e) { /* fine */ } };
      } else via.hidden = true;
      if (!m.childElementCount) {
        if (st.ready || askDoors.some(d => d.ready)) {
          const who = st.ready ? `<b>${esc(st.label || st.provider)}</b>, model <span class="mono">${esc(st.model)}</span>` : "the door you pick above";
          askNote(`<p>Ask anything about what is on this screen. The question goes with the screen's own numbers to ${who}, and nowhere else.${askDoors.length ? " The picker above chooses who answers." : ""} An answer worth keeping has a Save as note button under it; nothing is kept unless you press it.</p>`, "hint");
        } else {
          askNote(`<p>No AI is set yet. ${esc(st.why || "")} Pick a provider and paste a key on <a href="/settings">Settings</a>, under Your AI. A model running on this computer needs no key.</p>`, "hint");
        }
      }
    } catch (e) { /* the send will say */ }
    document.getElementById("askin").focus();
  }
  async function sendAsk() {
    if (askBusy) return;
    const ta = document.getElementById("askin");
    const question = ta.value.trim();
    if (!question) return;
    const { page, query, label } = askPage();
    askBusy = true; document.getElementById("asksend").disabled = true;
    ta.value = "";
    const qd = document.createElement("div"); qd.className = "q"; qd.textContent = question;
    const m = document.getElementById("askmsgs"); m.appendChild(qd);
    const wait = askNote(`<p class="wait">Reading ${esc(label)} and asking…</p>`);
    try {
      const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, page, query, history: askHistory.slice(-6), door: (document.getElementById("askvia") || {}).value || "" }) });
      const out = await r.json();
      if (!out.ok) {
        wait.className = "a err";
        wait.innerHTML = `<p>${esc(out.error || "The model did not answer.")}` +
          (out.settings ? ` Set it on <a href="/settings">Settings</a>, under Your AI.` : "") + `</p>`;
      } else {
        wait.innerHTML = out.answer.split(/\n{2,}/).map(p => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`).join("") +
          (out.read && out.read.length ? `<div class="rd">read ${out.read.map(esc).join(" · ")} · ${esc(out.model || "")}</div>` : "");
        askHistory.push({ role: "user", content: question }, { role: "assistant", content: out.answer });
        offerSave(wait, question, out, query, label);
      }
    } catch (e) {
      wait.className = "a err";
      wait.innerHTML = "<p>The desk did not answer. Is it still running?</p>";
    }
    askBusy = false; document.getElementById("asksend").disabled = false;
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
