/* GreekSoup.ai · landing page · one script, no framework */
(function () {
  "use strict";
  var d = document;
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* nav: compact after the hero, menu on phones */
  var nav = d.getElementById("nav");
  function onScroll() { nav.classList.toggle("compact", window.scrollY > 80); }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  var menu = d.getElementById("menu"), links = d.getElementById("navlinks");
  if (menu) menu.addEventListener("click", function () {
    var open = links.classList.toggle("open");
    menu.setAttribute("aria-expanded", open ? "true" : "false");
    menu.textContent = open ? "Close" : "Menu";
  });
  links.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", function () { links.classList.remove("open"); menu.textContent = "Menu"; menu.setAttribute("aria-expanded", "false"); }); });

  /* the operating-system switch, shared by every install field on the page */
  function setOS(os) {
    d.querySelectorAll("[data-os]").forEach(function (b) { b.setAttribute("aria-selected", b.dataset.os === os ? "true" : "false"); });
    d.querySelectorAll("[data-line='mac'],[data-line='win']").forEach(function (c) { c.hidden = c.dataset.line !== os; });
    try { localStorage.setItem("gs-os", os); } catch (e) {}
  }
  d.querySelectorAll("[data-os]").forEach(function (b) { b.addEventListener("click", function () { setOS(b.dataset.os); }); });
  var startOS = "mac";
  try { startOS = localStorage.getItem("gs-os") || (/Windows/.test(navigator.userAgent) ? "win" : "mac"); } catch (e) {}
  setOS(startOS);

  /* copy: the visible line in the same field */
  d.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var field = b.closest(".field");
      var code = Array.prototype.find.call(field.querySelectorAll("code"), function (c) { return !c.hidden; });
      var text = code ? code.textContent : "";
      function done() { b.textContent = "Copied"; setTimeout(function () { b.textContent = "Copy"; }, 1600); }
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, done);
      else { var ta = d.createElement("textarea"); ta.value = text; d.body.appendChild(ta); ta.select(); try { d.execCommand("copy"); } catch (e) {} d.body.removeChild(ta); done(); }
    });
  });

  /* install: the three ways */
  d.querySelectorAll(".seg [data-pane]").forEach(function (b) {
    b.addEventListener("click", function () {
      d.querySelectorAll(".seg [data-pane]").forEach(function (x) { x.setAttribute("aria-selected", x === b ? "true" : "false"); });
      d.querySelectorAll(".pane[data-pane]").forEach(function (p) { p.hidden = p.dataset.pane !== b.dataset.pane; });
    });
  });

  /* the screens index: the frame follows the row under the cursor */
  var show = d.getElementById("showimg"), showcap = d.getElementById("showcap"), rows = d.querySelectorAll("#index .row");
  var current = "flow", loaded = {};
  function src(name) { return "img/screen-" + name + ".webp"; }
  function preload(name) { if (loaded[name]) return; var i = new Image(); i.src = src(name); loaded[name] = i; }
  function swap(row) {
    var name = row.dataset.shot;
    rows.forEach(function (r) { r.classList.toggle("on", r === row); });
    if (showcap) showcap.textContent = row.dataset.cap;
    if (!show || name === current) return;
    current = name;
    if (reduced) { show.src = src(name); return; }
    show.classList.add("fade");
    var img = new Image();
    img.onload = function () { if (current !== name) return; show.src = src(name); show.classList.remove("fade"); };
    img.onerror = function () { show.classList.remove("fade"); };
    img.src = src(name);
  }
  rows.forEach(function (r) {
    r.addEventListener("mouseenter", function () { swap(r); });
    r.addEventListener("focus", function () { swap(r); });
    r.addEventListener("click", function (e) { e.preventDefault(); swap(r); });
  });
  var idle = window.requestIdleCallback || function (f) { setTimeout(f, 1200); };
  idle(function () { rows.forEach(function (r) { preload(r.dataset.shot); }); });

  /* reveal on first sight; the hero card opens and its line draws once */
  var card = d.getElementById("rubber");
  if (card && !reduced) { card.classList.add("open"); setTimeout(function () { card.classList.add("draw"); }, 250); }
  var targets = d.querySelectorAll("main > section > *:not(.hero-product), .fig, .fig1-wrap");
  if ("IntersectionObserver" in window && !reduced) {
    targets.forEach(function (el) { if (!el.closest(".hero")) el.classList.add("rv"); });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target, i = 0, sib = el;
        while ((sib = sib.previousElementSibling) && sib.classList.contains("rv") && !sib.classList.contains("in")) i++;
        setTimeout(function () { el.classList.add("in"); }, Math.min(i, 6) * 60);
        io.unobserve(el);
      });
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.05 });
    targets.forEach(function (el) { io.observe(el); });
  } else {
    targets.forEach(function (el) { el.classList.add("in"); });
  }

  /* releases: read from VERSION on GitHub, the file the desk itself reads */
  var URL = "https://raw.githubusercontent.com/shubhamsborkar/one-person-equity-research-desk/main/VERSION";
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function shortNote(t) {
    var cut = t.search(/[:;]/); if (cut > 24 && cut < 160) t = t.slice(0, cut);
    if (t.length > 150) { t = t.slice(0, 150); t = t.slice(0, t.lastIndexOf(" ")); }
    return t;
  }
  fetch(URL, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); }).then(function (text) {
    var rows = text.split("\n").map(function (l) { return l.trim(); }).filter(function (l) { return l && l[0] !== "#"; }).map(function (l) {
      var m = /^(\S+)\s+(.*)$/.exec(l); return m ? { v: m[1], t: m[2] } : { v: l, t: "" };
    });
    if (!rows.length) return;
    var ver = d.getElementById("ver"); if (ver) ver.textContent = rows[0].v;
    var rel = d.getElementById("rel");
    if (rel) rel.innerHTML = rows.slice(0, 8).map(function (r, i) {
      return '<li><span class="d">' + esc(r.v) + (i === 0 ? '<span class="cur">current</span>' : "") + '</span><span class="t">' + esc(shortNote(r.t)) + "</span></li>";
    }).join("");
    var note = d.getElementById("relnote");
    if (note) note.innerHTML = 'Read just now from <a href="https://github.com/shubhamsborkar/one-person-equity-research-desk/blob/main/VERSION">VERSION</a> on GitHub, the same file your desk reads when it checks for an update. The full note for each release is there.';
  }).catch(function () { /* the list in the page stands */ });
})();
