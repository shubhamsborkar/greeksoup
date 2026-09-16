# Technical notes

The README is written for a reader who hands the folder to a coding agent. This file is for the reader who wants to see what the agent does, or do it by hand.

## What this folder is, and what it is not

This folder is only the desk: the program that draws the fourteen tabs, the pages, the broker adapter and the data templates. It is not the Obsidian vault. The vault (your notes, the rulebook file, the raw inbox, the wiki and output folders, the skills) is a separate folder that the newsletter edition walks you through building, and the desk works with or without it. The two connect in two places only: the `obsidian/Live Desk.md` note, which shows the desk inside Obsidian, and the optional `VAULT_OUTPUT_DIR` setting, which drops the desk's daily reports into your vault as notes. The desk folder can sit anywhere on your computer, inside the vault or next to it.

Day to day you do not need the coding agent to run the desk; it starts with your computer (or with the start file) and you look at it in a browser or in Obsidian. The agent (Claude Code, Codex, Kimi Code, Grok Build, in a terminal or in its desktop app) is for setting it up, adapting it to your broker, and changing it later by describing what you want.

## Two desks for two markets

Desk · Home is two things on one page, built differently on purpose. The top is the broker account in whatever market you trade, and it can stay dark. The bottom is the US panels, which read the public record and need no broker at all, and sit there for every reader wherever the home market is, because a reader in any market holds and watches US names.

- **Desk · Home** is your broker account in whatever market you trade: holdings, open futures, funds, margin used as a bar, an options tape on the index, a ticker strip, a results calendar and the alert strip. It talks to the broker through one file in `brokers/`, chosen on Settings (`BROKER` in `.env`). Six ship: Alpaca, ICICI Direct (Breeze), Interactive Brokers (Flex Web Service), Tradier, Trading 212 and Zerodha (Kite Connect), all read-only. Every file returns holdings and cash; `server.py` marks any line without a price from Yahoo through the row's `ysym`. Everything beyond that is an optional function on the file (`brokers/README.md` lists them: `quote`, `history`, `intraday`, `futures`, `futures_quote`, `sparks`, `tape`, `stream`, `resolve`, `search`, `extra_accounts`, `commodities_local`), and the desk shows what exists: a broker whose file serves ticks and chains gets the live grid and the options tape, a broker that serves only holdings gets a smaller Home screen. With no broker chosen the desk boots with everything else live.
- **The market layer** (`markets/`, one file per home market) supplies what the market's public record offers, keyed by the broker file's `META["region"]`: session hours, the benchmark index and its label, currency and locale, the exchanges, the Yahoo suffix for an exchange symbol, and optionally the results calendar, the filings block for the home ticker page and the market's own macro cards. India (`in.py`: NSE hours, NIFTY 50, the NSE results calendar and integrated filings through `nse_fund.py`, the 10-year, repo rate and CPI cards) and the United States (`us.py`) ship. With no broker, `HOME_MARKET=in` or `us` in `.env` picks one; otherwise the home screens stay global and Watch · Home takes Yahoo symbols. The contract is `markets/README.md`.
- **The US panels** (`web/assets/usdesk.js` and `usdesk.css`, mounted under the broker book on Desk · Home) are the US market read from the public record and one optional feed: a hand-kept book of US positions priced live, the earnings countdown, the insider tape from Form 4 filings (with cluster buys), and a market pulse. They need no broker at all, so they work from anywhere, and the US intelligence tabs (Funds, Flow, Short, Capitol) sit on the same free sources. Until 2026-09-15.20 they were a screen of their own, Desk · US, shown only when the home market was the United States; `/usdesk` now lands on Desk · Home.

So a reader in the US runs Desk · Home on Alpaca, Interactive Brokers or Tradier with the US panels beneath; a reader in Australia has the agent write `brokers/<name>.py` for an ASX broker and `markets/au.py` for the ASX (both contracts are one README each); a reader in India picks either Indian broker and the India market file serves both. The labels are two strings at the top of `web/assets/desk.js`; rename them to your markets.

## What runs without any key

The desk is built to fetch whatever it can from the free record before it asks for a key. With no broker keys and no feed key it still boots, and this is what each tab does:

| Tab | With no key at all | What the feed key adds |
|---|---|---|
| The US panels of Desk · Home | Positions priced from Yahoo; earnings countdown from Yahoo; insider tape from SEC EDGAR (Form 4, your names); market pulse empty | Insider scan across the whole market; the movers and sector pulse |
| Watch · US, Global | Yahoo quotes, any Yahoo symbol from any exchange (`TALABAT.AE`, `0700.HK`, `ASML.AS`) | 50/200-day distance and market cap columns |
| Ticker page (`/t?symbol=X`) | Chart and quote from Yahoo, profile, ratios, targets and analyst counts from Yahoo when it is not rate-limiting, insider table from EDGAR | Statements, ratios history, segments, estimates, peers, dividends, news, the DCF seeds |
| Funds | 13F and 13D/G straight from EDGAR | Nothing, it never uses the feed |
| Flow | CBOE's free delayed chains | Nothing |
| Short | FINRA's free files | Nothing |
| Capitol | House disclosures read from the Clerk's public PDFs (the Senate site blocks scripts) | Both chambers, cleaner rows |
| Macro | FRED, free, plus the home market file's own cards | Nothing |
| Risk | Yahoo price histories, against the home market's index and the S&P 500 | Nothing |
| Chain | Your own map, priced from Yahoo | Nothing |

Two honest notes on the free paths. Yahoo's endpoints are unofficial and rate-limit bursts, so a fresh install can show "retry in a few minutes" on its first page loads; the desk backs off and retries. The first Capitol build downloads up to 150 recent House reports and reads them, which takes a minute or two once, then a few seconds a day.

## Setup, once (if you would rather do it yourself)

```
git clone https://github.com/shubhamsborkar/greeksoup.git
cd greeksoup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # optional: the Settings page writes this file for you
```

Then put your names in the files under *The files you edit* (or add them in the pages once the desk is up). Keys go on `/settings` once the desk is up: the page writes `.env` (only the names it knows, one line each, comments kept), tests the data key against the feed, sends one line to the AI model, takes the broker's daily token, and registers or removes the start-at-login service. The page never returns a key, only its last four characters. A plain-text page at `/agent` tells any AI agent on the machine which address serves what, and carries the reader's investing profile from `data/profile.json` (written by the same page) so an agent shapes its answers to the reader. `/api/settings/backup` streams `data/` and `research/` as one zip, never `.env`, tokens or `cache/`.

Or hand all of this to your agent, as the README describes.

## Keep the desk running

Two ways to run it. Pick one.

**Start it when you want it.** Double-click `Start Desk.command` (Mac) or `Start Desk.bat` (Windows), then open `http://localhost:8765`. Close the window and the desk stops.

**Always on.** Double-click `Keep Desk Running.command` (Mac) or `Keep Desk Running.bat` (Windows) once. From then on the desk starts by itself when you log in, and if it ever stops, for any reason, it is back within a few seconds. Shut the laptop and it sleeps with it; open the lid and it carries on. `Stop Desk.command` / `Stop Desk.bat` switches it off (and, on the Mac, back on). On the Mac this uses the built-in launch agent; on Windows it registers a task in Task Scheduler that runs `desk-service.ps1` hidden at logon. The Windows files were written from Microsoft's documented commands and have not been run on a Windows machine by the author; if one of them complains, paste the window's text to your coding agent and ask it to fix it, which is the same method that built the desk. On Linux the same thing is a five-line systemd user unit (`ExecStart=<folder>/.venv/bin/python server.py`, `WorkingDirectory=<folder>`, `Restart=always`, enabled with `systemctl --user enable --now`), and your agent can write it.

Nothing on the desk needs a login of its own: the US panels, the watch grids, Funds, Flow, Short, Capitol, Macro and Risk run from the public record and the optional feed key you set once.

Whether Desk · Home needs anything each day is up to your broker, not the desk. Most brokers keep an API session alive for weeks or months once the key is set. A broker file with `daily_login` set (the two Indian files as shipped) is the exception: that regulator requires a fresh login every trading day, so on a morning you want the Home page live you paste what the login redirect hands back on the Settings page (the file's `token_param` names it; `exchange_token` turns it into the day's token, cached in `session_token_primary.txt`), and the desk reconnects without a restart. A broker app whose redirect address is `http://localhost:8765/settings` delivers it to the page by itself. Skip the login and the desk keeps serving the last saved book re-priced live and shows a ribbon, and every other page is unaffected.

To have the desk inside Obsidian: switch on the **Web Viewer** core plugin, copy `obsidian/Live Desk.md` into your vault, and (optional) copy `obsidian/desk.css` into `.obsidian/snippets/` and enable it, so the note uses the full width.

The dated markdown reports (`python daily.py`: holdings, movers, options tape, futures positions, a static dashboard) are the same data as files; point `VAULT_OUTPUT_DIR` at a folder in your vault to read them there.

## The files you edit

All of them sit in the `data/` folder, plain JSON you can open in any text editor.

| File | What it is |
|---|---|
| `data/book.json` | The hand-kept book for anyone with no broker: Yahoo symbols from any market, shares, average cost, cash per currency. The Desk · Book page edits it (add, remove, paste-import). |
| `data/watchlist.json`, `data/watchlist_us.json`, `data/watchlist_global.json` | The three watch grids (also editable in the page). Home codes are your broker's stock codes when the broker serves quotes, else exchange symbols in the home market, else Yahoo symbols. |
| `data/fno_watchlist.json` | Names for the home options tape (indices and large caps), read by a broker file whose `tape` function serves chains. |
| `data/funds.json` | The 13F filers you follow (name + CIK). |
| `data/members.json` | Congress members tracked by name. |
| `data/supply_chain.json` | Your value-chain maps (an example ships). |
| `data/alerts.json` | Alert rules: day moves, margin used, futures expiry, earnings, price levels, insider clusters, 13Ds. Checked every minute; fires a macOS notification and an on-desk chip once per rule per day. |
| `data/watch_levels.json` | Optional price levels per holding. |
| `data/commodities.json` | The commodity board: 51 commodities, their free sources, and for each the industries a rise squeezes (`cost`) and helps (`revenue`). No company names, no country prices: it is the universal layer. |
| `data/exposure_us.json`, `data/exposure_<market>.json` | The names behind those industries for one market, with filing-sourced figures. `data/exposure_example.json` is the template; the README has the prompt that fills one. |

## How the update works

Two files at the root of the repository drive it. `VERSION` lists releases one per line, newest first, as a date and one line of notes; the first line is the current version. `MANIFEST.json` carries the sha256 of every tracked file in that version and, under `history`, every hash each file has ever shipped with on the branch (`scripts/make_manifest.py` writes it from the git history; line endings are folded before hashing so a Windows checkout matches the ZIP).

`updater.py` runs a daily check in a background thread: one keyless GET of the raw `VERSION` on `main`, cached for a day in `cache/update_check.json`, compared as strings against the local `VERSION`. `GET /api/update` serves the result (add `?check=1` to ask GitHub now); the shared page chrome in `web/assets/desk.js` draws the strip. `POST /api/update/apply` downloads the branch ZIP from codeload, unpacks it in a temporary folder, and walks the new manifest:

- `.env`, `cache/`, `logs/`, `output/`, the virtual environment and the daily tokens are never written.
- A program file or page is copied over when the local copy is absent or its hash appears in the file's history (it is some shipped version, unchanged here). A local file whose hash appears in no shipped version was changed on this computer, so it is kept as it is and listed in the reply and the strip for the agent to merge. Files removed upstream are left in place.
- Under `data/`, a file the reader lacks is added; `alerts.json` is merged by rule identity (type plus window, scope or symbol), so a threshold the reader tuned survives and only missing rules are appended; the desk's own reference tables (`commodities.json`, `exposure_us.json`, `exposure_example.json`) are refreshed only when the local copy is byte-identical to a shipped version. Every other file under `data/` is the reader's and is never touched.
- If `requirements.txt` changed, `pip install -r requirements.txt` runs with the desk's own interpreter.
- `VERSION` and `MANIFEST.json` land last, the report is written to `cache/update_result.json`, and the process replaces itself with `os.execv` on the same command line, so the new files take effect whether or not the always-on service is installed; the page's heartbeat reloads when the desk answers again.

`DESK_AUTO_UPDATE=on` in `.env` makes the daily thread apply a newer version without the click. `DESK_UPDATE_VERSION_URL` and `DESK_UPDATE_ZIP_URL` point a fork or a private mirror at its own `VERSION` and ZIP. To cut a release from a fork: edit `VERSION`, run `python scripts/make_manifest.py`, commit both. The README paste under *Getting a newer version* remains the manual path and does the same job through the agent.

## More than one account

A broker file that supports several accounts at the same broker hands the others back through its optional `extra_accounts` function (one shipped file does, with its account list in `breeze_session.py` and a key pair per account in `.env`); only the first account's session is required, and the others fall back to their last saved book, re-priced live. The other shipped files read one account each (Tradier takes an account number when the profile has several). Desk · Home reads one broker at a time; a US book sits in `data/us_book.json` beside it.

## Adapting to your broker and your market

Two short files, each with a README that is its contract.

- **The broker file**, `brokers/<name>.py`: `META`, `connect`, `label`, `equity` and `funds`, written to `brokers/README.md`, and one line in `REGISTRY`. Open this folder in your coding agent, give it the broker's API documentation and that README, and Desk · Home, Risk and the home watch grid light up. Everything else the README lists (`quote`, `history`, `intraday`, `futures`, `futures_quote`, `sparks`, `tape`, `stream`, `resolve`, `search`, `extra_accounts`, `commodities_local`) is optional and appears on the screens when the file has it; a broker whose codes differ from exchange symbols wants `resolve` and `search`, a broker that serves a book wants `quote`, and so on. Charles Schwab (weekly login), Upstox, Angel One and Groww (daily login) follow the same pattern; Fidelity, Vanguard and Robinhood publish no stock API for individuals, so their holdings go into Desk · Book from an export.
- **The market file**, `markets/<region>.py`: `META` (hours, index, currency, exchanges, Yahoo suffix), `is_open`, `ysym`, and optionally `results_calendar`, `fundamentals`, `macro_series` and `macro_cards`, written to `markets/README.md`, one line in its `REGISTRY`, and the broker file's `META["region"]` set to the same code. The shipped India file is the full example (the exchange's results calendar and filings, three macro cards from public statistics); the shipped US file is the minimal one.

The shipped India broker file reaches its broker through `breeze_session.py`, `collect.py`, `stream_in.py`, `pricing.py`, `fno.py`, `secmaster.py` and `local_in.py`; those files belong to that broker and nothing else in the desk imports them.

## Data sources

- Broker API: your account, through one of the six shipped broker files or one your agent writes; live ticks during market hours where the file serves them.
- SEC EDGAR, keyless: Form 4 insider filings on your names (`sec_form4.py`), plus the 13F and 13D/G feeds.
- Commodities (`commods.py`), all keyless: Yahoo's chart feed for exchange-traded contracts (gold, copper, crude, wheat, cotton ...), FRED's monthly IMF series for the long history of benchmarks with no contract, and one sentence per page from Trading Economics for those benchmarks' current level and day, month and year change (rubber, zinc, urea, coking coal, freight). The scraped sentence is date-stamped and the last good value persists, so a changed page degrades to stale, never to blank. A broker file's optional `commodities_local` attaches local price lines to the cards (the shipped India file adds MCX front-month futures through the broker's history endpoint and the Rubber Board of India's daily sheet); they appear only while that broker is connected, so a reader elsewhere never sees them.
- House Clerk, keyless: periodic transaction reports as PDFs, parsed with pypdf (`house_ptr.py`).
- Yahoo Finance, keyless: quotes, candles, and the ticker page basics when there is no feed (`freefeed.py`).
- Financial Modeling Prep (optional): US quotes, statements, estimates, peers, insider filings, Congress trades. The desk was built on the Starter plan; `scripts/audit_fmp.py` probes which endpoints your plan allows.
- SEC EDGAR: 13F and 13D/G filings, read directly. Set `EDGAR_CONTACT` in `.env`; the SEC asks for it.
- CBOE delayed option chains, FINRA short files, FRED, the home market file's public sources (the exchange's filings and results calendar, statistics offices), Yahoo Finance quotes and history: all free, no key.

Yahoo's free quotes are near live for US listings and 15 to 20 minutes delayed for most other exchanges. Yahoo's quote endpoints are unofficial and can change; the code degrades to the feed or to the last saved quotes when they do.

