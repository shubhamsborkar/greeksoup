/* greeksoup.ai · one script, no framework */
(function () {
  "use strict";
  var d = document, root = d.documentElement;
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* theme: one button, flips */
  function setTheme(t, save) {
    root.setAttribute("data-theme", t);
    if (save) { try { localStorage.setItem("gs-theme", t); } catch (e) {} }
  }
  var tb = d.querySelector("[data-theme-toggle]");
  if (tb) tb.addEventListener("click", function () { setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark", true); });
  setTheme(root.getAttribute("data-theme") || "dark", false);

  /* menu on small screens */
  var menu = d.getElementById("menu"), links = d.getElementById("navlinks");
  if (menu) menu.addEventListener("click", function () {
    var open = links.classList.toggle("open");
    menu.setAttribute("aria-expanded", open ? "true" : "false");
  });
  links.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", function () { links.classList.remove("open"); menu.setAttribute("aria-expanded", "false"); }); });

  /* operating system, shared by every install line */
  function setOS(os) {
    d.querySelectorAll("[data-os]").forEach(function (b) { b.setAttribute("aria-selected", b.dataset.os === os ? "true" : "false"); });
    d.querySelectorAll("[data-line='mac'],[data-line='win']").forEach(function (c) { c.hidden = c.dataset.line !== os; });
    try { localStorage.setItem("gs-os", os); } catch (e) {}
  }
  d.querySelectorAll("[data-os]").forEach(function (b) { b.addEventListener("click", function () { setOS(b.dataset.os); }); });
  var startOS = "mac";
  try { startOS = localStorage.getItem("gs-os") || (/Windows/.test(navigator.userAgent) ? "win" : "mac"); } catch (e) {}
  setOS(startOS);

  /* copy: the visible code in the same install line */
  d.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var box = b.closest("[data-install]");
      var code = Array.prototype.find.call(box.querySelectorAll("code"), function (c) { return !c.hidden; });
      var text = code ? code.textContent : "";
      var span = b.querySelector("span"), label = span ? span.textContent : "";
      function done() { if (span) { span.textContent = "Copied"; setTimeout(function () { span.textContent = label; }, 1500); } }
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, done);
      else { var ta = d.createElement("textarea"); ta.value = text; d.body.appendChild(ta); ta.select(); try { d.execCommand("copy"); } catch (e) {} d.body.removeChild(ta); done(); }
    });
  });

  /* the recording: it loops on its own; a reader who asked for less motion gets the poster */
  var vid = d.getElementById("deskvid");
  if (vid && reduced) { vid.removeAttribute("autoplay"); vid.pause(); vid.controls = true; }

  /* the screens: the list drives the frame */
  var show = d.getElementById("showimg"), showcap = d.getElementById("showcap"), showurl = d.getElementById("showurl");
  var rows = d.querySelectorAll(".screen-list [data-shot]"), current = "home", loaded = {};
  function src(n) { return "img/full-" + n + ".webp"; }
  function preload(n) { if (loaded[n]) return; var i = new Image(); i.src = src(n); loaded[n] = i; }
  rows.forEach(function (t) {
    t.addEventListener("click", function () {
      var n = t.dataset.shot;
      rows.forEach(function (x) { x.setAttribute("aria-selected", x === t ? "true" : "false"); });
      if (showcap) showcap.textContent = t.dataset.cap;
      if (showurl) showurl.textContent = "localhost:8765" + t.dataset.url;
      if (!show || n === current) return;
      current = n;
      if (reduced) { show.src = src(n); return; }
      show.classList.add("fade");
      var img = new Image();
      img.onload = function () { if (current !== n) return; show.src = src(n); show.classList.remove("fade"); };
      img.onerror = function () { show.classList.remove("fade"); };
      img.src = src(n);
    });
  });
  var idle = window.requestIdleCallback || function (f) { setTimeout(f, 1500); };
  idle(function () { rows.forEach(function (t) { preload(t.dataset.shot); }); });

  /* reveal on first sight, quietly; the hero card's line draws once */
  var card = d.getElementById("rubber");
  if (card && !reduced) card.classList.add("draw");
  var targets = d.querySelectorAll(".sec-head, .fig, .table3 .col, .pair > div, .way, .after-grid > div, .acc, .colophon-grid > div, .fig1-wrap");
  if ("IntersectionObserver" in window && !reduced) {
    targets.forEach(function (el) { el.classList.add("rv"); });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target, i = 0, sib = el;
        while ((sib = sib.previousElementSibling) && sib.classList.contains("rv") && !sib.classList.contains("in")) i++;
        setTimeout(function () { el.classList.add("in"); }, Math.min(i, 4) * 60);
        io.unobserve(el);
      });
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.05 });
    targets.forEach(function (el) { io.observe(el); });
  } else {
    targets.forEach(function (el) { el.classList.add("in"); });
  }

  /* releases: read from VERSION on GitHub, the file the desk itself reads */
  var URL = "https://raw.githubusercontent.com/shubhamsborkar/greeksoup/main/VERSION";
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function shortNote(t) {
    var cut = t.search(/[:;]/); if (cut > 24 && cut < 160) t = t.slice(0, cut);
    if (t.length > 150) { t = t.slice(0, 150); t = t.slice(0, t.lastIndexOf(" ")); }
    return t;
  }
  fetch(URL, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); }).then(function (text) {
    var rs = text.split("\n").map(function (l) { return l.trim(); }).filter(function (l) { return l && l[0] !== "#"; }).map(function (l) {
      var m = /^(\S+)\s+(.*)$/.exec(l); return m ? { v: m[1], t: m[2] } : { v: l, t: "" };
    });
    if (!rs.length) return;
    var rel = d.getElementById("rel");
    if (rel) rel.innerHTML = rs.slice(0, 5).map(function (r, i) {
      return '<li><span class="d">' + esc(r.v) + (i === 0 ? '<span class="cur">current</span>' : "") + '</span><span class="t">' + esc(shortNote(r.t)) + "</span></li>";
    }).join("");
    var note = d.getElementById("relnote");
    if (note) note.innerHTML = 'Read just now from <a href="https://github.com/shubhamsborkar/greeksoup/blob/main/VERSION">VERSION</a> on GitHub, the same file your desk reads when it checks for an update. <a href="docs/project/releases/">Every release</a>.';
  }).catch(function () { /* the list in the page stands */ });
})();
