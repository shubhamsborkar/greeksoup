# Security

GreekSoup runs on your own computer and answers only at an address your own computer can reach (`http://localhost:8765`). Nothing on it is hosted by us, and no account exists anywhere.

## What it talks to

The desk makes outbound requests to these places, and to nothing else:

- **Your broker**, only if you connected one, with the keys you gave it, read-only. The six shipped adapters (Alpaca, ICICI Direct, Interactive Brokers, Tradier, Trading 212, Zerodha) use each broker's documented read endpoints. None of them places an order.
- **The public record**: SEC EDGAR, FINRA, CBOE's delayed chains, FRED, the Senate and House disclosure sites, Yahoo Finance quotes, Trading Economics, and the India sources named on the Macro screen.
- **Your data provider**, only if you gave it a key (Financial Modeling Prep today).
- **Your AI**, only if you gave it a key or pointed it at a local model.
- **GitHub**, once a day, one small request for the `VERSION` file, to know whether a newer version exists. The update itself downloads the repository ZIP from GitHub when you click.
- **Google Fonts**, from the pages' markup, for the desk's typefaces.

There is no telemetry, no analytics, no crash reporting and no account. The desk sends nothing about you or your book anywhere. The daily version check carries no identifier.

## Where your keys live

In `.env` inside the desk folder, written by the Settings screen. The desk reads it at start. The updater never touches it, the backup zip never includes it, and the page an AI agent reads (`/agent`) tells the agent not to read it. Broker session tokens live beside it in `session_token*.txt`. Both are in `.gitignore`.

The Settings screen accepts writes only from a browser on the same computer sending JSON, which is the guard against a web page elsewhere posting to it.

## What it never does

It never places orders. There is no order path in the code, on any broker, and the `do_POST` handler says so. If you extend it to trade, that is your own build.

## Reporting a problem

If you find a security problem, open a GitHub issue titled `Security` with no details in it, and we will reply with a private channel within a few days. Please do not post the details publicly first.

## Keeping your copy safe

- Do not expose the port to the internet. The desk has no login of its own because it is not meant to be reachable by anyone but you.
- Back up from Settings before a big change. The backup carries your lists and data, never your keys.
- Every number on the desk comes from a feed that can be wrong, late or restated. Verify against the primary source before acting on anything.
