---
title: Contributing
nav: Contributing
description: How to add a broker, a market or a data provider to GreekSoup, and what every contribution keeps true.
lead: Most contributions are one file to a written contract, written by your agent and tested on your own desk. This is what has to stay true.
---

## The three contracts

- **A broker**: one file in `brokers/`, following `brokers/README.md`. It reads holdings and cash, and anything else the broker serves. It never places an order and never writes a key anywhere but the settings file.
- **A market**: one file in `markets/`, following `markets/README.md`. Session hours, the index, the currency, the exchanges, and where the public record offers them, the results calendar and the market's own macro cards.
- **A data provider**: one file in `data_providers/`, following `data_providers/CONTRACT.md`.

## What stays true

- No orders, and no order path.
- Public sources only for anything that runs without a key. Every scrape is dated. A failed fetch keeps the last good value.
- Nothing assumed. No broker, market, provider or country is the default; everything is picked from a list.
- Plain words for the reader. Anything a reader sees is written for an investor with no engineering background.
- A refusal from a source becomes one plain sentence on the screen, and the desk carries on.

## Sending it in

Fork the repository, make the change, run the checks (`python -m pytest tests -q`, which test the contracts and never the network), and open a pull request. The template asks four short questions. The full version of this page is `CONTRIBUTING.md` in the repository.

## Asking for one

If you want a broker or a market and would rather not write it, [open an issue](https://github.com/shubhamsborkar/greeksoup/issues/new/choose); there is a template for each.
