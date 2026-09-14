---
title: Another broker
description: Connect a broker GreekSoup does not ship a file for, with an AI agent and the broker's own documentation.
lead: Any broker that publishes an API is one file your agent writes from that broker's documentation. The shape it has to return is written down, and everything else in the desk works from that shape.
---

## Brokers the desk knows about, and the way in for each

Settings lists these under **Another broker**.

| Broker | The way in |
|---|---|
| Charles Schwab | Has an API for individuals. The login has to be repeated every seven days, so your agent writes this one from Schwab's documentation and keeps the weekly login. |
| Fidelity, Vanguard | No API for individuals. Export the holdings to a file and paste them into Desk · Book; most exports paste straight in. |
| Robinhood | No API for stocks. Export the holdings into Desk · Book, or have your agent connect Robinhood's own agent server. |
| Upstox, Angel One, Groww | Each has an API with a daily login, the same pattern as the two Indian brokers shipped, and the same Indian market file serves all of them. Your agent writes it from their documentation. |
| Any other | If it publishes an API, your agent writes the file. If it does not, Desk · Book takes an export. |

## The paste

Open the desk folder in your agent and paste, with the broker's name and where its documentation is:

```
Read brokers/README.md in this folder. Write brokers/<broker>.py for <broker> from its API documentation at <address>, to the shape that README describes: META, connect, label, equity and funds, read-only, with every refusal from the broker turned into one plain sentence. Add it to REGISTRY in brokers/__init__.py. If the broker's codes differ from exchange symbols, add resolve and search. If its market is not India or the United States, write markets/<region>.py to markets/README.md as well and set the broker's region to it. Then restart the desk and tell me what to paste on Settings.
```

The new broker appears in the list on Settings the next time the page loads, with the fields its file asks for.

## What the file has to return

Five things, and the desk does the rest: what the reader pastes (the fields), how to connect, a label for the account (the last four characters, never a name), the holdings, and the cash. Each holding is a row with the code, the quantity, the average cost, the last price if the broker gives one, the currency, and Yahoo's symbol for the same share; a row without a price is marked from Yahoo through that symbol.

Everything beyond that is optional and appears on the screens when the file has it: a live quote with the order book, daily and minute candles, open futures and options, a futures book, sparklines, the index options tape, live ticks, a symbol master for brokers whose codes differ from exchange symbols, several accounts at the same broker, and local commodity reads. The contract in the repository, `brokers/README.md`, lists each one's shape.

## The market side

A broker file names the market it trades in, and a file in the markets folder supplies that market's session hours, index, currency and public record. India and the United States ship; [your own market](/docs/markets/your-own-market/) is one short file more.

## Keeping it through updates

A file your agent wrote is yours. The update keeps it as it is and names it in the strip, so if a newer version of the desk changes the contract you can ask the agent to merge.
