# Security

GreekSoup runs on your own computer and answers only at an address your own computer can reach (`http://localhost:8765`). Nothing on it is hosted by us, and no account exists anywhere.

## What it talks to

The desk makes outbound requests to these places, and to nothing else:

- **Your broker**, only if you connected one, with the keys you gave it, read-only. The six shipped adapters (Alpaca, ICICI Direct, Interactive Brokers, Tradier, Trading 212, Zerodha) use each broker's documented read endpoints. None of them places an order.
- **The public record**: SEC EDGAR, FINRA, CBOE's delayed chains, FRED, the Senate and House disclosure sites, Yahoo Finance quotes, Trading Economics, and the India sources named on the Macro screen.
- **Your data provider**, only if you gave it a key (Financial Modeling Prep today).
- **Your AI**, only if you chose one: a key from a lab, an app you already pay for on this computer (Claude Code, Codex, Gemini CLI, Kimi Code, Grok Build, Qwen Code, Cursor, which reach their own providers under your own account), or a model running on your computer. What goes is your question and the numbers on the screen you asked from, when you press Enter.
- **GitHub**, once a day, one small request for the `VERSION` file, to know whether a newer version exists. The update itself downloads the repository ZIP from GitHub when you click.
- **Google Fonts**, from the pages' markup, for the desk's typefaces.

There is no telemetry, no analytics, no crash reporting and no account. The desk sends nothing about you or your book anywhere. The daily version check carries no identifier. The Tell us page gathers a report and shows it to you in full; it leaves your computer only when you press Send on that page (it then goes to our support address and is filed as a public issue on the repository, with your email, if you gave one, kept privately and never published) or when you send it from your own mail app.

## Where your keys live

In `.env` inside the desk folder, written by the Settings screen. The desk reads it at start. The updater never touches it, the backup zip never includes it, and the page an AI agent reads (`/agent`) tells the agent not to read it. Broker session tokens live beside it in `session_token*.txt`. Both are in `.gitignore`.

The Settings screen accepts writes only from a browser on the same computer sending JSON, which is the guard against a web page elsewhere posting to it.

## What it never does

It never places orders. There is no order path in the code, on any broker, and the `do_POST` handler says so. If you extend it to trade, that is your own build.

## Reporting a problem

If you find a security problem, write to info@shikshannivesh.com with `Security` in the subject, and we reply within a few days. Please do not post the details publicly first.

## Keeping your copy safe

- Do not expose the port to the internet. The desk has no login of its own because it is not meant to be reachable by anyone but you.
- Back up from Settings before a big change. The backup carries your lists and data, never your keys.
- Every number on the desk comes from a feed that can be wrong, late or restated. Verify against the primary source before acting on anything.

## The two guards

The desk has no login because nothing outside your computer can reach it. Two guards keep a web page you visit from reaching it either: every request must name this computer in its `Host` header (which refuses DNS rebinding), and every request from a browser must carry the desk's own `Origin` (which refuses a cross-site read or post). Programs on this computer send no `Origin` and are let through. The full threat model, the honest limits and the question of running it on a server are on https://greeksoup.ai/docs/project/security/.
