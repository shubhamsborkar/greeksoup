---
title: Your own market
description: Add a market GreekSoup does not ship, with one short file written by an AI agent to the markets contract.
lead: One short file, written to a contract in the repository, and every home screen takes your market's shape. An agent writes it from the exchange's public pages in a few minutes.
---

## The paste

Open the desk folder in your agent and paste, with your market's name:

```
Read markets/README.md in this folder. Write markets/<region>.py for <market> to that contract: the session hours, the benchmark index and its Yahoo symbol, the currency and its symbol and locale, the exchanges and the Yahoo suffix for each, and the economic calendar's country code. If the exchange publishes a results calendar or company filings a program can read, add results_calendar and fundamentals from its public pages, date-stamped, with the last good value kept when a fetch fails. Add the region to REGISTRY in markets/__init__.py, and set my broker file's region to it. Then restart the desk.
```

Pick **Home market** on Settings if no broker sets it, and the home screens change on their next refresh.

## What the file supplies, and what is optional

Required, and enough for the session dot, Risk, the currency and Watch · Home:

- The region code and a plain label.
- The currency, its symbol and how its digits group.
- The exchanges, the first one the default.
- The index Risk measures against, as a Yahoo symbol, and its label.
- The country code the economic calendar uses.
- Whether the market is open now, in your computer's local time.
- How to turn an exchange symbol into Yahoo's symbol (RR on the London Stock Exchange becomes `RR.L`).

Optional, and shown when the file has it:

- A results calendar for a list of symbols.
- The filings block for a ticker page: quarters, shareholding, announcements.
- The market's own macro rows and cards.

The contract in the repository, `markets/README.md`, gives the exact shape of each one. The shipped India file is the full example; the United States file is the minimal one.

## Two rules for the file

Keep it to public sources, and let a failed fetch return the last good value rather than nothing. Every figure on the desk names its source on the screen, and a market file is no exception.

## Keeping it through updates

A file your agent wrote is yours. The update keeps it as it is and names it in the strip, so if a newer version changes the contract you can ask the agent to merge.
