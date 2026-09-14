# Contributing

GreekSoup is built with an AI agent from plain-English descriptions, and most contributions arrive the same way: you describe what you want to your agent inside the folder, it writes the file, you test it on your own desk, and you send it in. This page says what a contribution has to keep true.

## The three contracts

Most useful contributions are one file to a written contract:

- **A broker**: one file in `brokers/`, following `brokers/README.md`. It reads holdings and cash, and anything else the broker serves (ticks, futures, margin, chains). It never places an order and never writes a key anywhere but the environment.
- **A market**: one file in `markets/`, following `markets/README.md`. Session hours, the index, the currency, the exchanges, and where the public record offers them, the results calendar and the market's own macro cards.
- **A data provider**: one file in `data_providers/`, following `data_providers/CONTRACT.md`. Sixteen functions, each returning the documented shape or `None`.

A contribution that adds to the desk itself (a screen, a column, a source) is welcome too. Open an issue first so we can agree on the shape.

## What stays true

- **No orders.** There is no order path and there will not be one in this repository.
- **Public sources only** for anything that ships keyless. Date-stamp every scrape. A failed fetch returns the last good value, never an exception to the reader.
- **Nothing assumed.** No broker, market, provider or country is the default. Everything is picked from a list.
- **Plain words for the reader.** Anything a reader sees on a screen or in the README is written for an investor with no engineering background. Engineering detail belongs in `TECHNICAL.md` and the contracts.
- **Refusals become one sentence.** When a source or a broker refuses, the screen says so in one plain line and the desk carries on.

## Sending it in

1. Fork, branch, make the change.
2. Run the checks: `python -m pytest tests -q`. They test the contracts, not the network.
3. If you changed what ships, add a line at the top of `VERSION` (date-stamped, newest first) and run `python scripts/make_manifest.py`.
4. Open a pull request. The template asks four questions; short answers are fine.

## Reporting

- **A bug**: the issue template asks for the log lines. `python doctor.py` in the desk folder prints everything useful and nothing private.
- **A broker or market you want**: there are templates for each.
- **A security problem**: see `SECURITY.md`.

## Licence

MIT. By contributing you agree your contribution is licensed the same way.
