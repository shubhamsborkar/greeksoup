---
title: "Open-source equity research software: what exists"
nav: Open-source field
description: The open-source equity research software an individual can actually run in September 2026: OpenBB after its wind-down, Ghostfolio, Portfolio Performance, the backtesting engines, and GreekSoup, the free one-person research desk. Licence, install effort and what each covers.
lead: Open source in finance splits into four kinds of thing, and most lists mix them up. Data platforms, portfolio trackers, backtesting engines and research desks each solve a different problem. Here is the field as it stands in September 2026, GreekSoup included, with the honest install effort next to each.
---

## Four kinds of thing

- **A data platform** fetches and normalises data from many providers for someone who writes code. OpenBB's Platform is the largest.
- **A portfolio tracker** records what you hold and reports performance. Ghostfolio and Portfolio Performance lead.
- **A backtesting engine** runs a trading rule over history. Lean, backtrader and Zipline are the known names.
- **A research desk** puts the record on screens for someone who reads filings and holds positions. GreekSoup is built as one.

## OpenBB

OpenBB started as Gamestonk Terminal in December 2020, an open-source command-line terminal, and became a Python data platform (the Open Data Platform, AGPL-3.0) with a web workspace on top that was the company's paid product. On 25 August 2026 the founder announced the company is winding down and releasing the entire product suite under a permissive licence. The code is large, capable and well documented. Running it means Python or Docker and a set of provider keys, and the question of who maintains it next is open as we write. For someone who writes code and wants a data layer to build on, it remains the deepest open-source work in the field.

## Ghostfolio

A privacy-first portfolio tracker, AGPL-3.0, self-hosted with Docker, PostgreSQL and Redis behind it. Stocks, ETFs and crypto, allocation and benchmark views, an anonymous sign-up. It tracks a portfolio well and stops there: no filings, no ownership data, no research notes. The install is a Docker compose file, easy if you have run one before and a real obstacle if you have not.

## Portfolio Performance

A free desktop application, GPL, that does performance accounting properly: internal rate of return, time-weighted return, many currencies, the full transaction history, all stored on your own machine. It is the tool for someone who wants the numbers on a portfolio done right and is happy importing CSV files. The interface is dense, the analytics are deep, and there is no research layer at all.

## The backtesting engines

QuantConnect's Lean, backtrader and Zipline are engines for testing a trading rule over history. They are for a quantitative workflow, and each assumes fluent Python. None of them is a research desk and none is meant to be.

## GreekSoup

GreekSoup is the research desk: sixteen screens on your own computer, under the MIT licence, installed with one pasted line on a Mac, Windows or Linux. Your broker book (six brokers read-only, any other one file to a written contract), a hand-kept book in any market, watchlists, risk, the 13F tracker from SEC EDGAR, the options tape from CBOE, FINRA short interest, Congress trades, the calendar of every dated event on your names, FRED macro, fifty-four commodities, your own value chains, and a research vault of plain files. Fifteen of the sixteen screens run with no key at all. An Ask box on every screen hands that screen's numbers to whichever AI you already use.

Two things set it apart in this list. It needs no code from the person using it: the install is one line, the settings are a screen, and changing the desk is a sentence to an AI agent. And it is a desk, so the first ten minutes after install are spent on the screens, with nothing to read first.

## Side by side

| | Kind | Licence | Install | Who it suits |
|---|---|---|---|---|
| OpenBB | Data platform and workspace | Permissive, per the August 2026 announcement | Python or Docker, provider keys | Someone who writes code and wants a data layer |
| Ghostfolio | Portfolio tracker | AGPL-3.0 | Docker compose | Someone who wants a self-hosted tracker |
| Portfolio Performance | Portfolio accounting | GPL | Desktop app | Someone who wants IRR and TWR done right |
| Lean, backtrader, Zipline | Backtesting | Various | Python | A quantitative workflow |
| GreekSoup | Research desk | MIT | One pasted line | Someone who reads filings and holds positions |

## How to pick

Someone asking "what do I hold and how has it done" wants Portfolio Performance or Ghostfolio. Someone who wants to build their own tooling in Python wants OpenBB's platform, and someone testing a trading rule wants Lean. Someone who researches companies and wants the record, the owners, the tape and their own notes on one desk, without writing code, is who GreekSoup was built for. [What runs with no key at all](/docs/get-started/no-key-needed/) is the fair place to start.
