/* A block a note can carry: three backticks, desk, then "hello AAPL MSFT" on a line. Two
   hooks make a block: registerFetch says where its data comes from (here, the desk's own
   quote block), register says how it is drawn. Copy this shape for a block of your own. */
(function () {
  if (!window.deskBlocks) return;
  window.deskBlocks.registerFetch("hello", async args => {
    const d = await (await fetch("/api/research/block?spec=" + encodeURIComponent("quote " + args.join(" ")))).json();
    return d.error ? d : { kind: "hello", rows: d.rows };
  });
  window.deskBlocks.register("hello", d =>
    `<div><b>Hello</b> from a plugin: ${d.rows.map(q => `<span class="mono">${q.symbol} ${q.price ?? "–"}</span>`).join(", ")}</div>`);
})();
