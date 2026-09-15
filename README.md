# GreekSoup: the one-person equity research desk

GreekSoup is a research desk that runs on your own computer: fourteen screens with your positions, the filings, the 13F and insider trades, the options tape, short interest, macro, a commodity board that names the industries each move squeezes or helps, and a page for any ticker, priced live. It reads the public record (SEC EDGAR, CBOE, FINRA, FRED, Yahoo), your broker if you connect one, and one optional data feed, and it opens in any browser at an address on your own computer.

You do not write any of it. One line pasted into a terminal installs it (below), and an AI coding agent (Claude Code, Codex, Kimi Code or Grok Build) can install it for you instead and changes it later when you ask. It is open source under the MIT licence, your keys stay in a file on your computer, and it updates itself. The edition that walks through every screen and the build is [How to Build a One-Person Equity Research Desk (a Mini Bloomberg) with Claude Fable](https://ai.shikshannivesh.com/p/how-to-build-a-one-person-equity); the screenshots there show the author's own copy, and this repository is that desk without the author's positions.

## How it works, in plain words

Three things are involved, and it helps to know which is which.

**The desk** is a small program that lives in the folder you download. When it is running, it shows its screens at an address in your browser. It runs on your computer, it stores everything on your computer, and it keeps running whether or not the agent is open.

**The agent** is the AI tool you type to. It installs the desk, connects your broker, and changes the desk when you ask for something new. You do not need it open to use the desk day to day.

**The data** comes from three places. Your broker knows what you own. The public record (SEC EDGAR for filings, CBOE for options, FINRA for short interest, FRED for macro, Yahoo for quotes) is free and needs no account. An optional paid feed adds the parsed financial statements on the ticker page and a few columns. If you skip the feed, nothing breaks.

## What you need

- A computer you leave on while you work. Mac, Windows or Linux.
- Optional: an AI coding agent (Claude Code, Codex, Kimi Code or Grok Build). It can do the install for you, and it is how you change the desk later by describing what you want. If you have none, search "how do I install Claude Code" and follow the two or three steps, or skip it and use the one-line install.
- Optional: an account with a broker that lets a program read it, which brokers call an API. The desk connects to Alpaca, ICICI Direct, Interactive Brokers, Tradier, Trading 212 and Zerodha as it comes, read-only, with what each hands out from its own dashboard; any other broker with an API is one file your agent writes from its documentation. Without one, you keep your holdings by hand on Desk · Book with Yahoo symbols, and the US desk and every intelligence screen still work.
- Optional: a Financial Modeling Prep key for the parsed financial statements on the ticker page.

## Install it: one line (about a minute)

On a Mac, press Command and Space together, type `Terminal`, press Enter; a plain window opens. Paste this line into it and press Enter:

```
curl -fsSL https://raw.githubusercontent.com/shubhamsborkar/one-person-equity-research-desk/main/install.sh | bash
```

On Windows, press the Windows key, type `PowerShell`, press Enter, then paste this line and press Enter:

```
irm https://raw.githubusercontent.com/shubhamsborkar/one-person-equity-research-desk/main/install.ps1 | iex
```

It finds Python on your computer (and installs it if it is missing), downloads the desk into a folder called GreekSoup in your home folder, installs what it needs into that folder and nothing else, sets the desk to start with your computer, starts it, and opens it in your browser. About a minute on a Mac; the Windows line was written from Microsoft's documented commands and has not been run on a Windows machine by the author, so if it complains, paste the window's text to an AI agent. Keys are optional. When you want one, open **Settings**, the last entry in the desk's sidebar, paste it there, and the desk keeps it in a file inside that folder; you never open the file yourself.

## Install it with an AI agent instead (about twenty minutes, the agent does the work)

Use this path if you already have an agent, or if you want it to connect your broker and fill in your keys for you.

1. **Get the folder.** Click the green **Code** button at the top of this page and choose **Download ZIP**. The file lands in your Downloads folder. Double-click it and a folder with the same name appears next to it; drag that folder into Documents. That folder is the desk, and everything below happens inside it.

2. **Get an agent, if you do not have one.** You do not need to know what a terminal is. Install the Claude desktop app from claude.ai/download (Codex, Kimi Code and Grok Build have their own apps and work the same way), sign in, and open its **Code** section. It asks which folder to work in: choose the desk folder you just moved to Documents. That is what "open the folder in your agent" means everywhere in this page. If you already use Claude Code in a terminal, open a terminal, type `cd ` (with the space), drag the desk folder onto the terminal window, press Enter, then type `claude` and press Enter.

3. **Paste this and press Enter:**

```
Read README.md in this folder and set the desk up for me on this computer. Install what it needs, copy .env.example to .env, and ask me for each key one at a time, telling me where to get it. My broker is <your broker>. If it is not the shipped one, read its API documentation and rewrite the broker adapter the way TECHNICAL.md describes. If I say I have no broker to connect yet, leave the broker keys empty and skip the adapter. Then start the desk, set it to start by itself whenever I log in using the Keep Desk Running file for my operating system (TECHNICAL.md explains it), and tell me the address to open.
```

4. **Answer its questions.** It will ask for your broker's key and, if you want one, the feed key, and it tells you where each comes from. If you have neither, say so and it skips them. It then installs everything, starts the desk, and gives you an address. Open that address in your browser. The whole thing takes about twenty minutes, most of it the agent working while you watch.

If anything goes wrong at any step, or at any point later, give your agent this file. Whether you use Claude Code, Codex, Kimi Code, Grok Build or any other agent, point it at the desk folder, tell it to read README.md, and describe the problem in your own words: it cannot install, the page is blank, the broker will not connect, you want a screen changed. Copy any error you see and paste it in. That is the whole method, and it is the same one that built the desk.

## Where the desk lives: the address

The desk opens at `http://localhost:8765`. "localhost" means *this computer*: the address is not a website, it is your own machine talking to itself, so nobody else on the internet can open it, and it works with no internet connection at all for the parts already loaded. `8765` is just the door number the desk answers on. Bookmark that address. If it does not open, the desk is not running, and the next section is what to do.

## Keeping it running

The folder you downloaded contains a few files whose names are plain English, and you use them by opening the folder (Finder on a Mac, File Explorer on Windows) and double-clicking the file. On a Mac the names end in `.command`, on Windows in `.bat`; you can ignore the ending.

- **Start Desk** starts the desk and keeps a small window open while it runs. Close that window and the desk stops. Use this if you only want the desk while you are at the screen.
- **Keep Desk Running** is the one to double-click once, if you want the desk to be there every time you sit down. From then on the desk starts by itself when you log in to your computer, and if it ever stops, for any reason, it is back within a few seconds without you doing anything. The agent's install instruction above already does this for you; the file is there for when you want to do it yourself or on a second computer.
- **Stop Desk** switches the always-on desk off. On a Mac, double-clicking it again switches it back on; on Windows, double-click Keep Desk Running again.

The Settings screen carries a switch, *Start with the computer*, that does what Keep Desk Running does, and shows whether it is on.

What happens in daily life once Keep Desk Running has been used: you shut the computer down and switch it on again, the desk is back once you log in. You close the laptop lid, the desk sleeps with it and carries on when you open the lid. Something crashes, the desk restarts itself. You never start it by hand again.

How to tell it is running: the address opens. If the page is blank, do these in order. First close that tab and open the address in a fresh tab, because a tab that once found the desk down keeps showing it down even after it is back, and a reload does not clear that. If the fresh tab is also blank, wait thirty seconds and open it again; the always-on service restarts the desk on its own. Then double-click Start Desk. Then, if it is still blank, give your agent this file and what the window says, and ask it to fix it.

Two honest notes. The Windows files were written from Microsoft's documented commands and have not been run on a Windows machine by the author; if one of them complains, the agent fixes it. And on the first ever start the Capitol screen downloads recent House disclosures and reads them, which takes a minute or two once; Yahoo's free quotes occasionally rate-limit a brand new install and show "retry in a few minutes", and the desk retries on its own.

## Every morning

Nothing, for most readers. The desk does not have a login of its own, and most brokers keep the connection to your account alive for months once the key is set.

The exception is a broker whose regulator requires a fresh login every trading day; of the brokers the desk ships, the two Indian ones are like that, and Settings says so next to the broker's name. On a morning you want that account live, open **Settings** in the desk, click *Open the broker login*, log in on the page it opens, copy the value the page tells you to from the address bar, paste it into the box and click *Connect*; Desk · Home is live a moment later. If you set the redirect address in your broker app to `http://localhost:8765/settings`, it arrives on its own after the login and there is nothing to copy. Skip the login and the desk keeps showing the last saved book, re-priced live, with a ribbon saying the broker session is off; every other screen is unaffected. Readers on any other broker never see this step.

## Two desks for two markets

The desk has two account screens, and they are built differently on purpose.

- **Desk · US** is the US market read from the public record and the optional feed: a book of US positions priced live, the earnings countdown, the insider tape from Form 4 filings with cluster buys, and a market pulse. It needs no broker, so it works from anywhere. If you invest in the US, this is your desk.
- **Desk · Home** connects to a broker account in whatever market you trade: holdings priced live, cash, and where the broker reports them, open futures and options, margin used and an options tape on the index. You pick the broker on Settings. Six connect as the desk comes, read-only, each with what it hands out from its own dashboard: Alpaca, ICICI Direct, Interactive Brokers, Tradier, Trading 212 and Zerodha. What the screen shows depends on what the broker gives: every one returns holdings and cash, and a line the broker does not price is marked from Yahoo's free feed; a broker that also serves live ticks, open futures and options, margin, or index option chains has those appear too, and a broker that serves none of them simply has a smaller Home screen. Any other broker with an API is one file your agent writes from that broker's documentation, to the shape described in the brokers folder, and Settings lists the brokers the desk knows about without a file and the way in for each. A broker with no API exports a file, and Desk · Book takes it.

The market follows the broker. Once a broker is connected, the desk knows which market it trades in, and the home screens take that market's shape: its session hours on the status dot, its index on the Risk screen, its currency and digit grouping, its exchanges in the add box on Watch · Home, and where that market's public record offers them, the results calendar on Desk · Home, the filings block on the home ticker page and the market's own macro cards. India and the United States ship; another market is one short file your agent writes from the description in the markets folder, and a reader with no broker can name a home market in Settings' file by hand.

So a reader in the US picks Alpaca, Interactive Brokers or Tradier and has both desks; a reader in the UK picks Trading 212 or Interactive Brokers; a reader in India picks either of the two Indian brokers; a reader in Australia has the agent write the file for an ASX broker, or keeps the book by hand while it is written.

## The fourteen screens

- **Desk · Home** and **Desk · US**: above.
- **Desk · Book**: a portfolio you keep by hand, for anyone with no broker to connect and no feed key. Any symbol Yahoo Finance knows, in any market (AAPL, RELIANCE.NS, MC.PA, 0700.HK); add a line in the page or paste your whole holdings list, and it is priced from Yahoo's free feed, US listings close to live and most other exchanges 15 to 20 minutes behind, with value, day move, profit since cost and weight, one currency at a time.
- **Risk**: beta, volatility, worst drawdown and correlation for every book against its index, leverage at underlying notional, margin cushion, a 5 percent stress line, sector concentration.
- **Watch · Home, Watch · US, Global**: three watch grids; add a name by typing it. Global takes any symbol from any exchange.
- **Macro**: 22 FRED series in groups, the home market's own cards, and an economic calendar for the US and the home market.
- **Funds**: 13F tracker straight from SEC EDGAR, top holdings, quarter-over-quarter changes, share of each company owned, plus the 13D/G activist feed.
- **Flow**: the options tape on every US name from CBOE's free delayed chains: put/call, open-interest walls, expected move, unusual strikes, day-over-day builds.
- **Short**: FINRA short interest and the daily short-volume ratio, kept apart.
- **Capitol**: Senate and House trading disclosures on your names, plus members you track.
- **Chain**: a value-chain map, receipt-graded and priced live.
- **Commodities**: 51 commodities in seven groups, from crude and copper to rubber, coking coal, palm oil, tea and the dollar against the rupee and the yuan, each with the level, five change windows and the distance from its five-year high. Click one and it shows the industries a rise squeezes and the industries it helps, the same in any country, and under each industry the listed names you have mapped to it, priced live, with the raw-material share from their own filings. A names-under-pressure panel adds up every commodity a name sits on and ranks who is squeezed and who is helped this month. It ships with the US names; you add your own market in one file (below).
- **Any ticker**: Cmd+K, type a symbol: chart, valuation, quality, estimates, insiders, dividends, news, and with a feed key six years of statements, ratios, segments, peers and a DCF sandbox.

And **Settings**, the last entry in the sidebar: your broker, picked from the list, with what it hands out and the daily login where a broker needs one; your data provider, with a button that says what your plan answers; your own AI, from any lab or a model running on your computer, with the request shape the endpoint speaks and a test; the address that lets any AI agent on your computer read the whole desk; a short page on how you invest (style, what you look at first, sectors, risk, holding period, your own words) that the agent page carries so any AI reading the desk answers you and not a stranger, two switches, *Start with the computer* and *Newer versions*, a list of your files with a one-click backup, and what to do when something is wrong. Nothing on it is required; every key is yours and stays on your computer.

## What runs with no key at all

With no broker key and no feed key the desk still starts, and twelve of the fourteen screens are live: Desk · US, Desk · Book, Watch · US, Global, Risk, Macro, Funds, Flow, Short, Capitol, Chain, Commodities, and the ticker page's chart, quote, ratios and insider table. The broker key lights up Desk · Home and Watch · Home. The feed key adds the parsed statements, ratio history, segments, estimates, peers, dividends and news on the ticker page, the 50 and 200 day columns on the US watch grid, a market-wide insider scan, and cleaner Congress rows.

## Your own market on the Commodities screen

The commodity board is the same everywhere: crude squeezes airlines and helps oil producers whether you are in Toronto or Chennai. What differs is the names. The desk ships `data/exposure_us.json`, the US names behind those industries, and `data/exposure_example.json`, a template for any other market. To add yours, open the desk folder in your agent and paste:

```
Read data/commodities.json and data/exposure_example.json. Build data/exposure_<my market>.json for the companies I follow in <my market>, one commodity at a time, from each company's latest annual report and results: the industry each name belongs to, the commodities it attaches to, its raw-material share of revenue with the document it came from, how long a commodity move takes to reach its margin, and what the company itself has said about passing costs on. Leave the figure empty where you cannot find a filing, never guess one.
```

The desk reads every `data/exposure_*.json` on the next rebuild. The figures in these files are annual and quarterly numbers, so refresh them once a quarter after results, with the same prompt.

## Changing it

Everything is a plain sentence to the agent. *Add Nvidia to my US watchlist. Follow Pershing Square on the Funds tab. Alert me when any holding moves 5 percent in a day. Add a tab that shows my dividend calendar.*

Your lists also sit as plain text files in the `data/` folder if you prefer to edit them yourself: your US positions (`us_book.json`), the three watch grids, the names for the options tape, the funds you follow, the Congress members you track, your value-chain maps, the alert rules, and optional price levels per holding. Each file has a comment at the top saying what goes in it.

The desk can hold several accounts at the same broker, and a US book next to a home account; the agent adds an account when you ask.

## Getting a newer version

The desk keeps growing (the list at the bottom of this section says what was added and when), and it tells you itself. Once a day it looks at the page you downloaded it from, and when a newer version exists a strip appears at the top of every screen with the date and what changed, and one button, **Update the desk**. Click it and the desk brings the new version in, keeps your keys and every list in your `data/` folder exactly as they are, adds any new list or alert rule, keeps any file your agent changed for you (a rewritten broker adapter, say) and names it so you can ask the agent to merge the changes into it, then restarts by itself. It takes under a minute. **Not now** hides the strip until the next version.

If you would rather not click at all, switch on *Newer versions* on the Settings screen. The desk then brings a new version in the day it appears and tells you what changed the next time you open it.

If a new version misbehaves, the desk kept the files it replaced, for the last three versions. Tell your agent "go back to the previous version of the desk", or in the desk folder type `python updater.py rollback`, then start the desk. Your keys, your lists and your caches are not part of that; only the desk's own files move.

Two more things in the folder, for the day you need them. **The check**: `python doctor.py` prints your Python version, whether the desk is answering, which keys are set by name and never by value, the last error lines from the log and which sources it can reach, so you can hand the printout to your agent or paste it into a bug report; nothing in it is private. **Uninstall Desk** (`.command` on a Mac, `.bat` on Windows, or `curl -fsSL https://greeksoup.ai/uninstall.sh | bash` on Mac and Linux) stops the desk, removes the start-at-login entry, saves your lists to the Desktop and asks before deleting the folder.

A copy from before 13 September 2026 does not have the strip yet, so bring it up to date once by hand, and from then on the desk tells you itself. Download the ZIP again from the green **Code** button, the same way as on install, so the new folder sits in your Downloads folder, then open your existing desk folder in your agent and paste:

```
A newer version of this desk is in my Downloads folder, in the folder that came out of the ZIP. Update this desk from it: bring over every program file and every page, keep my .env and everything in my data folder exactly as they are, add any file in the new data folder that mine does not have, add any alert rule from its data/alerts.json that mine is missing, then restart the desk and tell me what is new.
```

That paste also works on any copy, at any time, if you would rather not use the strip. If you took the desk with git instead of the ZIP, `git pull` in the desk folder does the same, and the agent restarts it.

What was added, newest first:

- **2026-09-15**: the Ask box. **Ask · your AI** at the bottom of the sidebar opens a box on every screen; your question goes with that screen's own numbers to the AI you set in Settings, and the answer comes back in the box. It describes what the numbers show and never says buy, sell or hold.
- **2026-09-14**: what a finished desk carries around itself. A check you run in the folder, an uninstall that saves your lists first and asks before deleting, an updater that keeps the last three versions and can go back, a security page, a contributing guide, issue templates, a check that runs on every change holding every broker and market file to its contract, and docs for your AI, data providers, data sources, what the desk talks to and what to do when something is wrong.
- **2026-09-13, later**: nothing in the desk assumes one broker or one country any more. A broker file is read for what it has (holdings and cash always; ticks, futures, margin, chains and a symbol master when the broker serves them), and the market the broker trades in supplies the session, the index, the currency, the results calendar, the filings and its own macro cards from a file in the markets folder (India and the United States ship). The daily-login helper files are gone; Settings does that job.
- **2026-09-13**: the desk looks for a newer version once a day and, when there is one, says so on every screen and brings it in with one click, keeping your keys, your lists and any file your agent changed.
- **2026-09-12**: the US names on the Commodities screen now carry their filed figures, 58 of 59, each with the document it came from; the one left blank says why. Three tickers corrected (Barrick is B, Solaris Energy Infrastructure is SEI, US Steel removed since it no longer trades).
- **2026-09-09**: the **Commodities** screen (51 commodities, the industries each one squeezes and helps, the names you map to them from their filings, a names-under-pressure panel, two new alert rules) and **Desk · Book**, the hand-kept portfolio for readers with no broker and no feed.
- **2026-09-03**: first public version, twelve screens.

## If you also use Obsidian

Optional, and nothing above depends on it. If you keep notes in Obsidian, the desk can appear as a tab inside it: in Obsidian, Settings, Core plugins, switch on **Web Viewer**; copy the note `obsidian/Live Desk.md` from the desk folder into your vault; open that note. The optional `obsidian/desk.css` file, dropped into your vault's `.obsidian/snippets/` folder and enabled under Appearance, lets the note use the full width. Or tell your agent: *put the desk inside my Obsidian vault*.

## For the technical reader

Setup by hand, the file map, how to adapt the broker adapter, the data sources in detail, and how the always-on service works on Mac, Windows and Linux: [TECHNICAL.md](TECHNICAL.md). What the desk talks to, where keys live and how to report a problem: [SECURITY.md](SECURITY.md). Adding a broker, a market or a data provider to its written contract, and the checks that run on every change: [CONTRIBUTING.md](CONTRIBUTING.md).

## Built with an agent

Every line here was written by Claude Code from plain-English descriptions and screenshots. The edition that walks through every screen, the build and the setup around it (the vault, the rulebook, the skills) is [How to Build a One-Person Equity Research Desk (a Mini Bloomberg) with Claude Fable](https://ai.shikshannivesh.com/p/how-to-build-a-one-person-equity) in the *Alpha with AI* newsletter.

The desk sits on top of a different setup, the agent itself as your research analyst: a folder of notes it reads, a rulebook it follows, and the habits of clipping filings into it and asking it questions. That is its own guide, and the place to start if you are new to all of this: [How I Set Up Claude Code as My Investment Research Analyst](https://ai.shikshannivesh.com/p/how-i-set-up-claude-code-as-my-investment), with its rebuild inside Obsidian in [How I Set Up Claude Code as My Investment Research Analyst 2.0](https://ai.shikshannivesh.com/p/how-i-set-up-claude-code-as-my-investment-c2b). The desk works with or without that setup.

## Disclaimer

This is an investment research tool, published for educational purposes by Shikshan Nivesh. Nothing in this repository, and nothing the desk shows, is investment, legal, or tax advice, a recommendation to buy, sell, or hold any security, or tailored to anyone's situation. The author is not a registered investment adviser or research analyst. The desk reads broker accounts, public filings, market data feeds and news sources; every number on it can be wrong, late, or misread, because feeds change, filings get restated, and code has bugs, so verify against the primary source before acting on anything. This copy places no orders. If you extend it to trade, you do so entirely at your own risk and under your own broker's and regulator's rules. Data from third-party providers is subject to their terms; a paid feed's data may not be redistributed. AI coding tools, including Claude Code, wrote this software. Investing carries risk, including the loss of capital. Do your own research and consult a qualified professional in your jurisdiction before making investment decisions.

## Licence

MIT, copyright Shikshan Nivesh and Shubham Borkar. See `LICENSE`. GreekSoup is a Shikshan Nivesh product; Alpha with AI is our newsletter.
