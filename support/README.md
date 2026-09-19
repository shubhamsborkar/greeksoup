# The support address

`worker.js` is the small script that receives a report sent from a reader's desk (the Send
button on the Tell us page) and files it as a public issue on the repository. It runs on
Cloudflare Workers, costs nothing at this size, and holds one secret: a GitHub token that can
open issues. The reader's email, if given, is kept in a small private store for ninety days
and never appears on the issue.

Setting it up, once (about fifteen minutes):

1. GitHub: a fine-grained token with **Issues: read and write** on `shubhamsborkar/greeksoup`
   and nothing else. Copy it.
2. Cloudflare dashboard: **Workers & Pages**, Create, name it `greeksoup-support`, paste
   `worker.js` over the starter code, Deploy.
3. In the Worker's **Settings**: under Variables and Secrets add `GITHUB_TOKEN` (secret, the
   token from step 1) and `REPO` (text, `shubhamsborkar/greeksoup`); under Bindings add a
   **KV namespace** named `EMAILS` (create a new namespace with the same name).
4. Copy the Worker's address (it ends in `.workers.dev`), add `/report` to it, and put it in
   `support.py` as the default `SUPPORT_URL`. Release. From that version on the Send button
   appears on every reader's Tell us page.

Reading a reader's email when a reply needs one: Cloudflare dashboard, Workers & Pages, KV,
the `EMAILS` namespace, key `email:<issue number>`.
