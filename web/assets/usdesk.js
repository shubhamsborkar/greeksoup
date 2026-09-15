/* The US panels of Desk · Home: the hand-kept US book, upcoming earnings, the US market pulse
   and the insider tape. Once Desk · US, a screen of their own that showed only when the home
   market was the United States; since 2026-09-15.20 they sit under the broker book on Desk ·
   Home for every reader, because a reader in any market holds and watches US names. Mount
   with mountUSDesk(rootElement). */
"use strict";
(function () {
  const MARKUP = `
  <div class="tiles" id="us_tiles"></div>
  <section class="panel">
    <div class="panel-h"><h2>Positions</h2><span class="sub" id="us_asof"></span></div>
    <div id="us_alloc"></div>
    <table><thead><tr>
      <th>Name</th><th>Shares</th><th>Avg cost</th><th>Live</th><th>Day %</th>
      <th>Value</th><th>P&amp;L</th><th>P&amp;L %</th><th>Weight</th><th>Decided by</th>
    </tr></thead><tbody id="us_rows"><tr><td class="dim" style="padding:26px">Loading…</td></tr></tbody></table>
  </section>
  <section class="panel">
    <div class="panel-h"><h2>Upcoming earnings</h2><span class="sub" id="us_esub">US names on the book and watchlist</span></div>
    <div class="erail" id="us_erail"><span class="dim" style="font-size:12px">Loading calendar…</span></div>
  </section>
  <section class="panel">
    <div class="panel-h"><h2>US market pulse</h2><span class="sub" id="us_psub"></span></div>
    <div class="secrow" id="us_secrow"></div>
    <div class="pulse3" id="us_pulse3"><span class="dim" style="font-size:12px;padding:14px">Loading movers…</span></div>
  </section>
  <section class="panel">
    <div class="panel-h"><h2>Insider tape</h2><span class="sub" id="us_isub">open-market Form 4 buys · whole market</span></div>
    <div id="us_insours"></div>
    <div class="pulse3" style="grid-template-columns:1fr" id="us_insclusters">
      <span class="dim" style="font-size:12px;padding:14px">Loading insider feed…</span></div>
  </section>
  <section class="panel"><div class="note" id="us_note"></div></section>
`;

function usd(x,dp=2){ if(x==null||isNaN(x))return "—";
  return (x<0?"−$":"$")+Math.abs(x).toFixed(dp).replace(/\B(?=(\d{3})+(?!\d))/g,","); }
function pct(x){ return x==null?"—":(x>=0?"+":"−")+Math.abs(x).toFixed(2)+"%"; }
function cls(x){ return x==null?"dim":(x>=0?"pos":"neg"); }
function tile(l,v,k,s,extra){return `<div class="tile"><div class="l">${l}</div><div class="v mono ${k||""}">${v}</div><div class="s">${s||""}</div>${extra||""}</div>`;}

/* allocation heat strip: positions by weight of the whole book, cash included */
function allocBar(d){
  if(!d.total) return "";
  let seg="";
  for(const p of [...d.positions].sort((a,b)=>(b.value||0)-(a.value||0))){
    const wt=(p.value||0)/d.total*100; if(wt<0.3) continue;
    const dp=p.day_pct;
    const alpha = dp==null?0:Math.min(88,28+Math.abs(dp)*16);
    const col = dp==null ? "var(--line2)"
      : `color-mix(in srgb,var(--${dp>=0?"pos":"neg"}) ${alpha.toFixed(0)}%,var(--panel2))`;
    seg+=`<a class="as" href="/t?symbol=${p.symbol}" style="width:${wt.toFixed(2)}%;background:${col}"
      title="${p.symbol} · ${wt.toFixed(1)}% of book · day ${dp==null?"—":(dp>=0?"+":"−")+Math.abs(dp).toFixed(2)+"%"}">${wt>=7?`<span>${p.symbol}</span>`:""}</a>`;
  }
  const cwt=(d.cash||0)/d.total*100;
  if(cwt>0.5) seg+=`<a class="as" style="width:${cwt.toFixed(2)}%;background:var(--panel2);cursor:default"
    title="cash · ${cwt.toFixed(1)}% of book">${cwt>=7?"<span style='color:var(--muted)'>CASH</span>":""}</a>`;
  return `<div class="alloc">${seg}</div>
    <div class="alloc-cap">allocation of the whole book · colour = today's move · cash grey</div>`;
}

async function pull(){
  const r = await fetch("/api/usbook"); const d = await r.json();
  const prog = d.mandate ? (d.total/d.mandate*100) : null;
  document.getElementById("us_tiles").innerHTML =
    tile("Book value", usd(d.total,0), "", "positions + cash") +
    tile("Deployed", usd(d.deployed,0), "", (d.total?(d.deployed/d.total*100).toFixed(1):"—")+"% of book") +
    tile("Cash", usd(d.cash,0), "", d.cash_note||"") +
    tile("Open P&L", (d.total_pnl>=0?"+":"")+usd(d.total_pnl,0), cls(d.total_pnl), "on deployed capital") +
    tile("Mandate", usd(d.mandate,0), "", prog!=null?prog.toFixed(1)+"% there · heading to $50k in 2026":"",
      prog!=null?`<div class="bar"><i style="width:${Math.min(100,prog)}%"></i></div>`:"");
  let html="";
  for(const p of d.positions){
    const wt = d.total ? (p.value/d.total*100) : null;
    html+=`<tr>
      <td class="name"><a href="/t?symbol=${p.symbol}">${p.symbol}</a><span class="co">${p.name||""}</span></td>
      <td class="mono">${p.shares}</td>
      <td class="mono">${usd(p.avg_cost)}</td>
      <td class="mono" style="font-weight:700">${usd(p.ltp)}</td>
      <td class="mono ${cls(p.day_pct)}">${pct(p.day_pct)}</td>
      <td class="mono">${usd(p.value)}</td>
      <td class="mono ${cls(p.pnl)}">${p.pnl==null?"—":(p.pnl>=0?"+":"−")+usd(Math.abs(p.pnl)).slice(1)}</td>
      <td class="mono ${cls(p.pnl_pct)}">${pct(p.pnl_pct)}</td>
      <td class="mono dim">${wt!=null?wt.toFixed(1)+"%":"—"}</td>
      <td class="dim" style="font-size:11px">${p.decided_by||""}</td></tr>`;
  }
  document.getElementById("us_rows").innerHTML=html;
  document.getElementById("us_alloc").innerHTML=allocBar(d);
  document.getElementById("us_asof").textContent="positions as recorded "+d.as_of+" · prices live via FMP · click a ticker for full research";
  document.getElementById("us_note").innerHTML =
    `Positions come from <b>data/us_book.json</b> in the desk folder; prices are live. Edit the file
     after any trade and this desk follows. <b>Connect a US broker:</b> if yours offers an API
     (Interactive Brokers, Alpaca, Robinhood and most large brokers do), open the desk folder in your
     AI agent and ask it to replace the file read with a live pull; its keys then go on
     <a href="/settings" style="color:var(--accent)">Settings</a> like the others.`;
}
async function pullEarnings(){
  try{
    const r=await fetch("/api/earnings"); const d=await r.json();
    const today=new Date();
    let html="";
    for(const e of d.rows){
      const dd=Math.max(0,Math.round((new Date(e.date)-today)/864e5));
      const k=dd<=7?"soon":(dd<=21?"near":"far");
      const dt=new Date(e.date+"T12:00:00");
      const when=dt.toLocaleDateString("en-US",{weekday:"short",month:"short",day:"numeric"});
      html+=`<div class="ecard ${e.tag==="held"?"held-c":""}">
        <span class="dd mono ${k}">${dd===0?"today":dd+"d"}</span>
        <div class="tick"><a href="/t?symbol=${e.symbol}">${e.symbol}</a>${e.tag==="held"?'<span class="held">HELD</span>':""}</div>
        <div class="when">${when}</div>
        <div class="est mono">EPS est <b>${e.eps_est??"—"}</b><br>Rev est <b>${e.rev_est?("$"+(e.rev_est/1e9).toFixed(1)+"B"):"—"}</b></div>
      </div>`;
    }
    document.getElementById("us_erail").innerHTML=html||'<span class="dim" style="font-size:12px">Nothing scheduled in the next 120 days.</span>';
    document.getElementById("us_esub").textContent=d.note||"soonest first · red ≤1wk, amber ≤3wk · home-market results come from the exchange calendar";
  }catch(e){}
}
async function pullPulse(){
  try{
    const r=await fetch("/api/pulse"); const d=await r.json();
    document.getElementById("us_psub").textContent=d.note||
      ((d.sector_date?`sectors as of ${d.sector_date} · `:"")+"movers refresh every 15 min · whole market, small caps included");
    document.getElementById("us_secrow").innerHTML=(d.sectors||[]).map(s=>
      `<span class="sec">${s.sector}<b class="${cls(s.chg)}">${pct(s.chg)}</b></span>`).join("");
    const col=(title,rows)=>`<div class="pcol"><h3>${title}</h3>${rows.map(x=>
      `<div class="prow"><a href="/t?symbol=${x.symbol}">${x.symbol}</a>
       <span class="nm">${x.name||""}</span>
       <span class="mono dim">${x.price!=null?usd(x.price):""}</span>
       <span class="mono ${cls(x.chg_pct)}">${pct(x.chg_pct)}</span></div>`).join("")}</div>`;
    document.getElementById("us_pulse3").innerHTML=
      col("Biggest gainers",d.gainers||[])+col("Biggest losers",d.losers||[])+col("Most active",d.actives||[]);
  }catch(e){}
}
function usdShort(v){
  if(v>=1e9)return "$"+(v/1e9).toFixed(1)+"B";
  if(v>=1e6)return "$"+(v/1e6).toFixed(1)+"M";
  return "$"+Math.round(v/1e3)+"k";
}
async function pullInsiders(){
  try{
    const r=await fetch("/api/insiders"); const d=await r.json();
    if(d.error){document.getElementById("us_insclusters").innerHTML=
      `<span class="dim" style="font-size:12px;padding:14px">${d.error}</span>`;return;}
    document.getElementById("us_isub").textContent=
      `open-market Form 4 buys ≥ $${(d.min_buy_usd/1000)}k · trailing ${d.window_days}d · refreshed ${d.ts}`+(d.note?` · ${d.note}`:"");
    const ours=d.our_buys||[];
    document.getElementById("us_insours").innerHTML = ours.length
      ? `<div class="secrow">${ours.slice(0,12).map(b=>
          `<span class="sec"><a href="/t?symbol=${b.symbol}" style="color:var(--accent);text-decoration:none;font-weight:800">${b.symbol}</a>
           ${b.who} <span style="opacity:.65">${b.role}</span><b class="pos">${usdShort(b.value)}</b>
           <span style="opacity:.5;font-weight:400"> ${b.date.slice(5)}</span></span>`).join("")}
         </div>`
      : `<div class="secrow"><span class="dim" style="font-size:11px">No open-market buys on book or watchlist names in the window.</span></div>`;
    const rows=(d.clusters||[]).slice(0,20).map(c=>
      `<div class="prow" ${c.ours?'style="background:rgba(237,90,36,.06)"':''}>
        <a href="/t?symbol=${c.symbol}">${c.symbol}</a>
        <span class="mono" style="min-width:70px">${c.n_buyers} buyers</span>
        <span class="mono pos" style="min-width:70px">${usdShort(c.total_value)}</span>
        <span class="nm">${c.buyers.slice(0,4).map(b=>`${b.who} (${b.role} ${usdShort(b.value)})`).join(" · ")}${c.buyers.length>4?" · +"+(c.buyers.length-4)+" more":""}</span>
        <span class="mono dim" style="font-size:10px">${c.first.slice(5)}→${c.last.slice(5)}</span>
        ${c.ours?'<span class="sec" style="color:var(--accent);border-color:var(--accent)">OURS</span>':''}
      </div>`).join("");
    document.getElementById("us_insclusters").innerHTML =
      `<div class="pcol"><h3>Cluster buys — 2+ distinct insiders, same name</h3>${rows||'<div class="prow"><span class="dim">None in the window.</span></div>'}</div>`;
  }catch(e){}
}


  window.mountUSDesk = function (root) {
    root.innerHTML = `<div class="us-head"><h2>The US desk</h2><span>the hand-kept US book, the earnings ahead, the market pulse and the insider tape, for every reader wherever the home market is</span></div>` + MARKUP;
    pull(); pullEarnings(); pullPulse(); pullInsiders();
    setInterval(pull, 30000); setInterval(pullPulse, 900000); setInterval(pullInsiders, 3600000);
  };
})();
