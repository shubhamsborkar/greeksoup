---
title: What runs with no key at all
nav: No key needed
description: Which GreekSoup screens are live with no broker and no data feed, and what each optional key adds.
lead: The desk is built to fetch whatever it can from the free record before it asks for a key. Here is the line between the two.
---

## With no key at all

Thirteen of the fifteen screens are live the moment the desk starts: the US panels of Desk · Home, Desk · Book, Watch · US, Global, Risk, Macro, Funds, Flow, Short, Capitol, Chain, Commodities, Notes, and the ticker page's chart, quote, ratios and insider table.

| Screen | With no key | What the feed key adds |
|---|---|---|
| The US panels of Desk · Home | Positions priced from Yahoo; earnings countdown from Yahoo; insider tape from SEC EDGAR on your names; market pulse empty | The insider scan across the whole market; the movers and sector pulse |
| Watch · US, Global | Yahoo quotes, any Yahoo symbol from any exchange | The fifty and two hundred day distance and market cap columns |
| Ticker page | Chart and quote from Yahoo; profile, ratios, targets and analyst counts from Yahoo when it is not rate-limiting; insider table from EDGAR | Statements, ratio history, segments, estimates, peers, dividends, news, the DCF seeds |
| Funds | 13F and 13D/G straight from EDGAR | Nothing; it never uses the feed |
| Flow | CBOE's free delayed chains | Nothing |
| Short | FINRA's free files | Nothing |
| Capitol | House disclosures read from the Clerk's public PDFs (the Senate site blocks programs) | Both chambers, cleaner rows |
| Macro | FRED, plus the home market's own cards | Nothing |
| Risk | Yahoo price histories against the home market's index and the S&P 500 | Nothing |
| Chain | Your own map, priced from Yahoo | Nothing |

## What the broker key adds

Desk · Home and Watch · Home. Holdings and cash from every broker; live ticks, open futures and options, margin and the index options tape where the broker serves them. The market the broker trades in then shapes the home screens, see [Markets](/docs/markets/).

## What the feed key adds

The parsed statements, ratio history, segments, estimates, peers, dividends and news on the ticker page, the fifty and two hundred day columns on the US watch grid, a market-wide insider scan, and cleaner Congress rows. The desk was built on Financial Modeling Prep's Starter plan; Settings has a button that says what your plan answers.

## Two honest notes on the free paths

Yahoo's endpoints are unofficial and rate-limit bursts, so a fresh install can show "retry in a few minutes" on its first page loads; the desk backs off and retries on its own. The first Capitol build downloads up to a hundred and fifty recent House reports and reads them, which takes a minute or two once, then a few seconds a day.
