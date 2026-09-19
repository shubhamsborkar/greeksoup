---
title: The three contracts
nav: Contracts
description: What a broker file, a market file and a data provider file must answer for GreekSoup to light up its screens, each a short file written to a README in the repository, usually by an AI agent from the provider's own documentation.
lead: A broker, a market or a data provider the desk does not ship is one short file, written to a README that is its contract. An AI agent writes it from the provider's documentation in an afternoon. This page is the three contracts in outline; each README in the repository is the full one.
---

## A broker: `brokers/<name>.py`

**Required**: `META` (the broker's name, its market as a region code, what it needs from the reader), `connect`, `label`, `equity` (the holdings) and `funds` (the cash and margin), plus one line in the registry. With those, Desk · Home, Risk and Watch · Home light up.

**Optional, and each appears on the screens when the file has it**: `quote`, `history`, `intraday`, `futures`, `futures_quote`, `sparks`, `tape`, `stream`, `stream_healthy`, `resolve`, `search`, `extra_accounts`, `commodities_local`. A broker whose codes differ from exchange symbols wants `resolve` and `search`; a broker that serves a book wants `quote`; a broker with a daily session keeps the day's key in its own file and Settings grows the login box for it.

The contract: `brokers/README.md`. The six that ship are the examples; the ICICI Direct file is the full one. [Another broker](/docs/brokers/another-broker/).

## A market: `markets/<region>.py`

**Required**: `META` (session hours, the index, the currency, the locale, the exchanges, Yahoo's suffix), `is_open`, `ysym` (the Yahoo symbol for an exchange code), and one line in the registry. The broker file's `META["region"]` names the same code, or the reader picks the country on Settings.

**Optional**: `results_calendar`, `fundamentals` (the exchange's own filings and results for a ticker page), `macro_series` and `macro_cards` (the market's own cards on Macro), and a local layer of the commodity board.

The contract: `markets/README.md`. The India file is the full example, the US file the minimal one. [Your own market](/docs/markets/your-own-market/).

## A data provider: `data_providers/<name>.py`

One file that answers the same questions the shipped provider answers, each returning plain Python or `None` when the provider does not have it, never raising: `quote`, `profile`, `income`, `balance`, `cashflow`, `ratios_ttm`, `estimates`, `segments`, `peers`, `dividends`, `news`, `history`, `insiders_latest`, `senate_latest`, `shares_float`. Settings keeps the provider's name, key and address. A read the provider cannot answer leaves one plain line on the screen.

The contract: `data_providers/CONTRACT.md`. [Data providers](/docs/setup/data-providers/).

## How to have one written

Open the desk folder in Claude Code, Codex, Gemini CLI or another agent, give it the provider's API documentation and the README, and say which of the three you want. From inside the desk, the Ask box in Build mode does the same. [Contributing](/docs/project/contributing/) is the way to send it back so the next reader has it.
