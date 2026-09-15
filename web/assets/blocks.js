/* Live blocks inside a note. A fenced ```desk block names a block and its arguments; the
   desk answers the data at /api/research/block and this file draws it in place, so a note
   carries live numbers next to the reader's words. A note that is mostly blocks is a
   dashboard. The registry below is the plugin surface: a plugin adds a renderer with
   window.deskBlocks.register(name, fn) and reads any desk address for its data. */
"use strict";
(function () {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const num = (v, d = 2) => (v === null || v === undefined || isNaN(v)) ? "–" : Number(v).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d });
  const pct = v => (v === null || v === undefined || isNaN(v)) ? "" : `<span class="${v >= 0 ? "pos" : "neg"}">${v >= 0 ? "+" : ""}${Number(v).toFixed(2)}%</span>`;
  const TYPE_LABEL = { general: "Note", news: "News", insight: "Insight", concall: "Call", meeting: "Meeting", risk: "Risk", answer: "AI answer", document: "Document", model: "Model", clipping: "Clipping", decision: "Decision", exit: "Exit", project: "Project" };
  const STATUS_LABEL = { watchlist: "Watchlist", researching: "Researching", "thesis built": "Thesis built", invested: "Invested", exited: "Exited" };

  function sparkline(values, w = 560, h = 120) {
    const xs = values.filter(v => v !== null && v !== undefined && !isNaN(v));
    if (xs.length < 2) return "";
    const lo = Math.min(...xs), hi = Math.max(...xs), span = (hi - lo) || 1;
    const pts = values.map((v, i) => v === null || v === undefined || isNaN(v) ? null : [i / (values.length - 1) * w, h - 6 - (v - lo) / span * (h - 12)]).filter(Boolean);
    const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    const up = xs[xs.length - 1] >= xs[0];
    return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" class="bk-spark"><path d="${d}" fill="none" stroke="${up ? "var(--pos)" : "var(--neg)"}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
  }

  const R = {
    quote(d) {
      return `<table class="bk-t"><thead><tr><th>Name</th><th class="r">Last</th><th class="r">Day</th><th class="r">As of</th></tr></thead><tbody>` +
        d.rows.map(q => q.error ? `<tr><td class="mono">${esc(q.symbol)}</td><td colspan="3" class="muted">${esc(q.error)}</td></tr>` :
          `<tr><td><a class="mono" href="/t?symbol=${encodeURIComponent(q.symbol)}">${esc(q.symbol)}</a>${q.name ? `<span class="muted"> ${esc(q.name)}</span>` : ""}</td><td class="r mono">${num(q.price)}${q.currency ? ` <span class="muted">${esc(q.currency)}</span>` : ""}</td><td class="r mono">${pct(q.day_pct)}</td><td class="r muted mono">${esc(q.ts)}</td></tr>`).join("") + `</tbody></table>`;
    },
    chart(d) {
      const c = d.closes || [], first = c.find(v => v !== null), last = [...c].reverse().find(v => v !== null);
      const chg = first && last ? (last - first) / first * 100 : null;
      return `<div class="bk-h"><a class="mono" href="/t?symbol=${encodeURIComponent(d.symbol)}">${esc(d.symbol)}</a> <span class="muted">${esc(d.range)}</span> <span class="mono">${num(last)}</span> ${pct(chg)} <span class="muted">${esc((d.dates || [])[0] || "")} to ${esc((d.dates || []).slice(-1)[0] || "")}</span></div>${sparkline(c)}`;
    },
    watch(d) {
      return (d.project ? `<div class="bk-h">${esc(d.project)} <span class="muted">${d.rows.length} names</span></div>` : "") + R.quote(d);
    },
    commodity(d) {
      const c = d.card, ch = c.chg || {};
      return `<div class="bk-h"><b>${esc(c.label)}</b> <span class="muted">${esc(c.group)} · ${esc(c.unit)}</span> <span class="mono">${num(c.value)}</span> <span class="muted">${esc(c.date)}${c.stale ? " · stale" : ""}</span></div>` +
        `<div class="bk-row">${["1d", "1w", "1m", "3m", "1y"].map(k => `<span><span class="muted">${k}</span> ${pct(ch[k])}</span>`).join("")}${c.from_all_high !== undefined ? `<span><span class="muted">from all-time high</span> ${pct(c.from_all_high)}</span>` : ""}</div>` +
        (c.spark ? sparkline(c.spark, 560, 80) : "");
    },
    status(d) {
      const s = d.status || {};
      return `<div class="bk-h"><a class="mono" href="/t?symbol=${encodeURIComponent(s.symbol)}">${esc(s.symbol)}</a> ${s.status ? `<b>${esc(STATUS_LABEL[s.status] || s.status)}</b> <span class="muted">${s.set_by === "you" ? "since " + esc(s.since) : "(what the desk can see)"}</span>` : `<span class="muted">no status yet</span>`}</div>` +
        ((s.history || []).length ? `<div class="bk-row muted">${s.history.slice(-5).map(h => `<span>${esc(h.at.slice(0, 10))} · ${esc(STATUS_LABEL[h.status] || h.status || "cleared")}</span>`).join("")}</div>` : "");
    },
    notes(d) {
      return d.rows.length ? `<div class="bk-list">${d.rows.map(n => `<a href="/notes?id=${encodeURIComponent(n.id)}"><span class="ty">${esc(TYPE_LABEL[n.type] || n.type)}</span>${esc(n.title)}${n.period ? ` <span class="muted">${esc(n.period)}</span>` : ""}<span class="muted r">${esc(n.updated)}</span></a>`).join("")}</div>` : `<div class="muted">no notes on this name yet</div>`;
    },
    tasks(d) {
      const o = d.tasks.open || {}, rows = [].concat(o.overdue || [], o.today || [], o.week || [], o.later || [], o.undated || []);
      return rows.length ? `<div class="bk-list">${rows.map(t => `<span><span class="ty">${esc(t.category || "task")}</span>${esc(t.text)}${t.symbol ? ` <span class="mono muted">$${esc(t.symbol)}</span>` : ""}${t.due ? ` <span class="${(o.overdue || []).includes(t) ? "neg" : "muted"}">due ${esc(t.due)}</span>` : ""}</span>`).join("")}</div><div class="muted"><a href="/notes?tasks">all tasks</a></div>` : `<div class="muted">nothing open</div>`;
    },
    timeline(d) {
      const t = d.timeline;
      return t.count ? `<div class="bk-cols">${t.groups.map(g => `<div><div class="ty" style="margin-bottom:3px">${esc(g.period || "no period")}</div>${g.items.map(it => it.what === "status" ? `<div class="muted"><span class="mono">${esc(it.date)}</span> · status ${esc(STATUS_LABEL[it.status] || it.status)}</div>` : `<div><span class="mono muted">${esc(it.date)}</span> <a href="/notes?id=${encodeURIComponent(it.id)}">${esc(it.title)}</a></div>`).join("")}</div>`).join("")}</div>` : `<div class="muted">nothing about ${esc(t.symbol)} yet</div>`;
    },
    book(d) {
      const p = d.book.positions || [];
      return p.length ? `<table class="bk-t"><thead><tr><th>Name</th><th class="r">Units</th><th class="r">Avg cost</th>${p[0].value !== undefined ? '<th class="r">Value</th><th class="r">Weight</th>' : ""}</tr></thead><tbody>${p.map(x => `<tr><td><a class="mono" href="/t?symbol=${encodeURIComponent(x.symbol)}">${esc(x.symbol)}</a>${x.name ? `<span class="muted"> ${esc(x.name)}</span>` : ""}</td><td class="r mono">${num(x.shares, 2)}</td><td class="r mono">${num(x.avg_cost)}</td>${x.value !== undefined ? `<td class="r mono">${num(x.value, 0)}</td><td class="r mono">${x.weight !== undefined ? num(x.weight, 1) + "%" : ""}</td>` : ""}</tr>`).join("")}</tbody></table>` : `<div class="muted">the book is empty</div>`;
    },
  };

  const F = {};   // fetchers a plugin registers: name -> async (args, spec) => data with a kind
  async function render(el, spec) {
    el.className = "bk";
    el.innerHTML = `<div class="bk-spec mono">${esc(spec)}</div><div class="bk-body muted">reading…</div>`;
    let d;
    const name = (spec.trim().split(/\s+/)[0] || "").toLowerCase();
    try {
      if (F[name]) d = await F[name](spec.trim().split(/\s+/).slice(1), spec);
      else d = await (await fetch("/api/research/block?spec=" + encodeURIComponent(spec))).json();
      if (d && !d.kind && !d.error) d.kind = name;
    } catch (e) { d = { error: "the desk did not answer" }; }
    const body = el.querySelector(".bk-body");
    if (d.error) { body.className = "bk-body bk-err"; body.textContent = d.error + (d.known ? " · known: " + d.known.join(", ") : ""); return; }
    const fn = R[d.kind];
    if (!fn) { body.className = "bk-body bk-err"; body.textContent = "no renderer for " + d.kind; return; }
    try { body.className = "bk-body"; body.innerHTML = fn(d); } catch (e) { body.className = "bk-body bk-err"; body.textContent = "could not draw this block"; }
  }
  function hydrate(root) {
    (root || document).querySelectorAll("[data-desk-block]").forEach(el => { if (!el.dataset.done) { el.dataset.done = "1"; window.deskBlocks.render(el, el.dataset.deskBlock); } });
  }
  /* the plugin surface: register(name, draw) gives a block its drawing, registerFetch(name, fn)
     gives it its data (fn gets the arguments and must return an object; the desk's own
     /api/research/block answers when no fetcher is registered) */
  window.deskBlocks = { register(name, fn) { R[name] = fn; }, registerFetch(name, fn) { F[name] = fn; }, render, hydrate, kinds: () => Object.keys(R) };
})();
