---
title: What it talks to
nav: What it talks to
description: Every place GreekSoup sends a request, what it sends, and what it never sends. No telemetry, no account, no analytics.
lead: The desk runs on your computer and answers only to your computer. This is the whole list of places it reaches out to, so you can decide with your eyes open.
---

## The list

- **Your broker**, only if you connected one, with the keys you gave it, read-only. Each shipped broker file uses that broker's documented read endpoints and none of them can place an order.
- **The public record**: SEC EDGAR for filings, FINRA for short interest, CBOE for delayed option chains, FRED for macro series, the Senate and House disclosure sites for Congress trades, Yahoo Finance for quotes and history, Nasdaq for US earnings dates, dividends and the market pulse, Trading Economics for a few commodity benchmarks, Frankfurter for central-bank reference exchange rates, OpenFIGI when you search by ISIN, the Bureau of Labor Statistics' release schedule and the Federal Reserve's meeting calendar for the US prints ahead, Forex Factory's public weekly file for the majors' prints this week, the India sources named on the Macro screen, and with India as the home market the Indian Mandi Prices API (mandi-api.onrender.com) and the Rubber Board of India for the Commodities board.
- **The website, not the desk**: greeksoup.ai counts its own page views and visits with Cloudflare Web Analytics, which sets no cookie and keeps no personal data, so we know how many people read the page. The desk itself sends nothing to Cloudflare or to us.
- **On Yahoo Finance, plainly**: the filings, the short interest, the option chains, the macro series and the Congress trades come from the bodies that publish them. Quotes and price history come from Yahoo's free feed, which has no contract behind it, throttles when asked too often, and can change without notice. The desk caches what it read and falls back where it can, a connected broker prices the names it knows, and a data provider key adds the statements and ratios. If you want a contract behind your prices, connect the broker or the provider; the free feed is where the desk starts.
- **Your data provider**, only if you gave it a key. Financial Modeling Prep ships today.
- **Your AI**, only if you chose one: a key from a lab, an app you already pay for on this computer (Claude Code, Codex, Gemini CLI, Kimi Code, Grok Build, Qwen Code, Cursor, which reach their own providers under your own account), or a model running on your own computer, which never leaves it. What goes: your question and the numbers on the screen you asked from, which on Desk · Home are your book. Nothing goes until you press Enter.
- **GitHub**, once a day, one small request for the `VERSION` file, to know whether a newer version exists. The update itself downloads the desk's files from GitHub when you click the button.
- **greeksoup.ai**, once, when you open the Plugins tab of Settings, for the list of plugins we publish.
- **Google Fonts**, for the desk's typefaces.

That is the list. Nothing else.

## What it never sends

Nothing about you, your book, your lists or your keys goes anywhere. There is no telemetry, no analytics, no crash reporting and no account. The daily version check carries no identifier; it is the same request a browser makes when it opens a page.

## Where your keys live

In one settings file inside the desk folder, written by the Settings screen and read when the desk starts. The update never touches it, the backup never includes it, and the page your AI app reads tells the AI not to read it either.

## What runs on your computer

Two things, both by your choice. **Sign in** under Your AI opens a terminal window running that app's own sign-in, which continues in your browser; the desk never sees the login. And a plugin's door runs the one command it names, with the Ask box's brief on standard input. Nothing else is run.

## The address

The desk answers at `http://localhost:8765`, which means "this computer" and nothing beyond it. It has no login of its own because nobody else can reach it, and two guards keep a web page you visit from reaching it either: every request must name this computer as its host, and every request from a browser must come from the desk's own pages. Do not point it at the internet; if you want it on another computer, install it there. [Your computer or a server](/docs/install/your-computer-or-a-server/).

## If you want to check

The desk's own check prints every setting by name and never by value, plus which of the sources above it can reach from your computer. In the desk folder: `python doctor.py`. Give the printout to your agent or paste it into a bug report; nothing in it is private.
