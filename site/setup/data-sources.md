---
title: Data sources
nav: Data sources
description: Every source behind GreekSoup's sixteen screens, what each one feeds, and which need a key.
lead: The source is named on every screen. This is the same list in one place, with what each one feeds.
---

## Free, no key

- **SEC EDGAR.** Form 4 insider filings on your names, the 13F filings of every fund you follow with what changed since the last one, and 13D and 13G activist filings. The SEC asks for a contact e-mail with each request, which you set once in Settings.
- **FINRA.** Short interest, twice a month, and the daily short-volume ratio, kept on separate lines on purpose.
- **CBOE.** Delayed option chains on every US name on your desk: put/call, the walls, the paid-for move, unusual strikes and open-interest builds.
- **FRED.** Twenty-two macro series in groups, and the long monthly history of commodity benchmarks that have no exchange contract.
- **The Senate and the House.** Trading disclosures on your names and on the members you follow; the House reports arrive as PDFs and the desk reads them.
- **Yahoo Finance.** Quotes, candles and the ticker page basics for any listing, and the exchange-traded commodity contracts on the board. Near live for US listings, fifteen to twenty minutes delayed for most other exchanges. Yahoo's quote endpoints are unofficial and can change; when they do, the desk falls back to the last saved quote and says so.
- **Nasdaq.** The earnings date and the dividend record of each US name on the Calendar, and the US market pulse on Desk · Home: every large and mega cap with today's move, volume and sector, from which the gainers, the losers, the most active by dollars traded and the sector snapshot are read.
- **Trading Economics.** One dated sentence per page for the commodity benchmarks with no contract and no FRED series, for the current level and the day, month and year change.
- **The home market's own sources.** The exchange's filings and results calendar, and the statistics office, for the market your broker trades in. India and the United States ship.

## With a key

- **Your broker.** Holdings and cash always; live ticks, futures, margin, chains and a symbol master where the broker serves them. Six ship. [Brokers](/docs/brokers/).
- **Your data provider.** The parsed financials, estimates, peers and the rest. [Data providers](/docs/setup/data-providers/).
- **Your AI.** [Your AI](/docs/setup/your-ai/).

## How a source failing shows up

A failed fetch never blanks a screen. The last good value stays, with its date, and the screen says the source is stale. Scrapes are date-stamped for the same reason.
