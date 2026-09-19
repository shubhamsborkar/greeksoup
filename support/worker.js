// GreekSoup support address. Runs on Cloudflare Workers. One job: take a report a
// reader sent from the Tell us page of their desk and file it as a public issue on the
// repository, then hand back the number and the link. The reply we write on that issue
// is read back by the desk, so the reader is answered where they already are.
//
// What it never does: publish the reader's email (kept privately, keyed by issue number,
// for ninety days), accept anything but a report, or take more than five reports an hour
// from one address.
//
// Settings on the Worker (Cloudflare dashboard, Settings, Variables and Secrets):
//   GITHUB_TOKEN   secret; a fine-grained token with Issues: read and write on the repository
//   REPO           "shubhamsborkar/greeksoup"
//   EMAILS         a KV namespace binding, for the private email store
//
// Deploy: paste this file into a new Worker named greeksoup-support, add the three settings,
// and give the desk its address (DESK_SUPPORT_URL, or the constant in support.py).

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method !== "POST" || url.pathname !== "/report") {
      return json({ ok: false, error: "This address takes reports from the GreekSoup desk and nothing else." }, 404);
    }
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    const key = "rate:" + ip + ":" + Math.floor(Date.now() / 3600000);
    const used = parseInt((await env.EMAILS.get(key)) || "0", 10);
    if (used >= 5) return json({ ok: false, error: "too many reports from this address in the last hour" }, 429);

    let body;
    try { body = await request.json(); } catch (e) { return json({ ok: false, error: "the report could not be read" }, 400); }
    const what = String(body.what || "").trim().slice(0, 4000);
    const check = String(body.check || "").trim().slice(0, 12000);
    const screen = String(body.screen || "").trim().slice(0, 200);
    const version = String(body.version || "").trim().slice(0, 40);
    const email = String(body.email || "").trim().slice(0, 200);
    if (!what) return json({ ok: false, error: "the report says nothing about what happened" }, 400);

    const title = ("From the desk: " + what.split("\n")[0]).slice(0, 120);
    const issueBody =
      "Sent from a reader's desk through Tell us" + (version ? ", version " + version : "") + (screen ? ", on " + screen : "") + ".\n\n" +
      "**What happened**\n\n" + what + "\n\n" +
      (check ? "<details><summary>The desk's check</summary>\n\n```\n" + check + "\n```\n</details>\n" : "") +
      "\n_The reader's email, if given, is held privately and is not on this page._";

    const r = await fetch("https://api.github.com/repos/" + env.REPO + "/issues", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + env.GITHUB_TOKEN,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "greeksoup-support",
      },
      body: JSON.stringify({ title, body: issueBody, labels: ["from-the-desk"] }),
    });
    if (r.status !== 201) {
      return json({ ok: false, error: "the repository did not take the report (" + r.status + ")" }, 502);
    }
    const issue = await r.json();
    await env.EMAILS.put(key, String(used + 1), { expirationTtl: 3600 });
    if (email) await env.EMAILS.put("email:" + issue.number, email, { expirationTtl: 90 * 86400 });
    return json({ ok: true, number: issue.number, url: issue.html_url });
  },
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json" } });
}
