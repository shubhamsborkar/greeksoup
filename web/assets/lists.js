/* The reader's own lists: one drawer for every list a screen runs on (funds, members, macro
   series, commodities, the options tape). Loaded on every page by desk.js; it attaches a
   "Your list" button to the screen that runs on a list, and the drawer does Add, Edit,
   Remove with Undo, and Bring the starters back. Nothing here is written until Save. */
(function () {
  "use strict";
  const SCREENS = { "/funds": "funds", "/capitol": "members", "/macro": "macro", "/commods": "commodities" };
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }).then(r => r.json());
  let VIEW = null, EDITING = null;   // the list on screen; the row being edited (null = none, {} = a new one)

  function drawer() {
    let el = document.getElementById("listdrawer");
    if (el) return el;
    el = document.createElement("aside");
    el.id = "listdrawer";
    el.innerHTML = `<div class="ld-h"><b id="ld-title"></b><button type="button" class="ld-x" title="Close">×</button></div><div class="ld-body" id="ld-body"></div>`;
    document.body.appendChild(el);
    el.querySelector(".ld-x").onclick = close;
    document.addEventListener("keydown", e => { if (e.key === "Escape" && el.classList.contains("on")) close(); });
    return el;
  }
  function close() { const el = document.getElementById("listdrawer"); if (el) el.classList.remove("on"); EDITING = null; }

  async function open(kind) {
    const el = drawer();
    el.classList.add("on");
    document.getElementById("ld-title").textContent = "Loading…";
    try { VIEW = await (await fetch("/api/lists/" + kind, { cache: "no-store" })).json(); } catch (e) { VIEW = null; }
    EDITING = null;
    render();
  }

  function fieldInput(f, v) {
    if (f.type === "list") return `<textarea data-f="${esc(f.key)}" placeholder="one per line">${esc((v || []).join ? v.join("\n") : v || "")}</textarea>`;
    if (f.type.startsWith("select:")) {
      const opts = f.type.slice(7).split("|");
      return `<select data-f="${esc(f.key)}">${opts.map(o => `<option value="${esc(o)}" ${v === o ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>`;
    }
    return `<input data-f="${esc(f.key)}" value="${esc(v || "")}" ${f.required ? "required" : ""}>`;
  }
  function form(row) {
    const isNew = !row || !Object.keys(row).length;
    return `<div class="ld-form"><h4>${isNew ? "Add a " + esc(VIEW.one) : "Edit"}</h4>` +
      VIEW.fields.map(f => `<label><span>${esc(f.label)}${f.required ? "" : " <i>optional</i>"}</span>${fieldInput(f, row ? row[f.key] : "")}</label>`).join("") +
      `<div class="ld-btns"><button type="button" class="ld-save">Save</button><button type="button" class="ld-cancel ghost">Cancel</button><span class="ld-msg" id="ld-msg"></span></div></div>`;
  }
  function render() {
    const body = document.getElementById("ld-body");
    if (!VIEW) { document.getElementById("ld-title").textContent = "Your list"; body.innerHTML = `<p class="ld-hint">The list could not be read. Reload the page and try again.</p>`; return; }
    document.getElementById("ld-title").textContent = VIEW.label;
    const name = VIEW.fields[0].key, key = VIEW.key;
    let h = `<p class="ld-hint">${esc(VIEW.hint)} Your rows live in your research vault; the screen rebuilds after a change.</p>`;
    if (EDITING) h += form(EDITING.row);
    else h += `<div class="ld-btns"><button type="button" class="ld-add">+ Add a ${esc(VIEW.one)}</button>` +
      (VIEW.hidden_starters ? `<button type="button" class="ld-back ghost">Bring the starters back (${VIEW.hidden_starters})</button>` : "") + `</div>`;
    h += `<div class="ld-rows">` + (VIEW.rows.length ? VIEW.rows.map(r => `<div class="ld-row" data-k="${esc(r[key])}">` +
      `<span class="ld-name">${esc(r[name])}</span><span class="ld-key mono">${name === key ? "" : esc(r[key])}</span>` +
      (r.starter ? `<span class="ld-st">starter</span>` : "") +
      `<button type="button" class="ld-edit" title="${r.starter ? "Make it yours" : "Edit"}">✎</button><button type="button" class="ld-rm" title="${r.starter ? "Put this starter away" : "Remove"}">×</button></div>`).join("")
      : `<p class="ld-hint">Nothing on the list yet.</p>`) + `</div>`;
    body.innerHTML = h;
    const add = body.querySelector(".ld-add"); if (add) add.onclick = () => { EDITING = { row: {}, was: "" }; render(); };
    const back = body.querySelector(".ld-back"); if (back) back.onclick = async () => { const out = await post(`/api/lists/${VIEW.kind}/starters`); if (out.ok) { VIEW = out.list; render(); } };
    body.querySelectorAll(".ld-row").forEach(el => {
      const k = el.dataset.k, row = VIEW.rows.find(r => String(r[key]) === k);
      el.querySelector(".ld-edit").onclick = () => { EDITING = { row: { ...row }, was: k }; render(); body.querySelector(".ld-form").scrollIntoView({ block: "nearest" }); };
      el.querySelector(".ld-rm").onclick = () => remove(row, k);
    });
    const save = body.querySelector(".ld-save");
    if (save) {
      save.onclick = async () => {
        const row = {};
        body.querySelectorAll("[data-f]").forEach(i => row[i.dataset.f] = i.value);
        const msg = document.getElementById("ld-msg"); msg.className = "ld-msg"; msg.textContent = "Saving…";
        const out = await post(`/api/lists/${VIEW.kind}/save`, { row, was: EDITING.was || "" });
        if (!out.ok) { msg.className = "ld-msg err"; msg.textContent = out.error || "That did not save."; return; }
        VIEW = out.list; EDITING = null; render();
      };
      body.querySelector(".ld-cancel").onclick = () => { EDITING = null; render(); };
      body.querySelectorAll("[data-f]").forEach(i => i.addEventListener("keydown", e => { if (e.key === "Enter" && i.tagName !== "TEXTAREA") { e.preventDefault(); save.click(); } }));
      const first = body.querySelector("[data-f]"); if (first) first.focus();
    }
  }
  async function remove(row, k) {
    const label = row[VIEW.fields[0].key];
    if (row.starter && !confirm(`Put away "${label}"? Bring the starters back is in this drawer.`)) return;
    const out = await post(`/api/lists/${VIEW.kind}/remove`, { key: k });
    if (!out.ok) { alert(out.error || "That did not work."); return; }
    VIEW = out.list; render();
    if (out.kind === "own" && window.deskToast) window.deskToast(`"${label}" removed.`, "Undo", async () => {
      const u = await post(`/api/lists/${VIEW.kind}/undo`, { undo: out.undo }); if (u.ok && u.list) { VIEW = u.list; render(); }
    });
  }
  function button(kind, label) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "listbtn"; b.textContent = label || "Your list";
    b.title = "Add, edit or remove what this screen runs on";
    b.onclick = () => open(kind);
    return b;
  }
  function attach() {
    const kind = SCREENS[location.pathname];
    if (kind) {
      const slot = document.querySelector("header .right");
      if (slot && !slot.querySelector(".listbtn")) slot.prepend(button(kind));
    }
  }
  window.deskLists = { open, button, attach };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", attach); else attach();
})();
