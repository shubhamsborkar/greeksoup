---
title: The files that are yours
nav: Your files
description: Every file GreekSoup keeps for the reader, plain JSON and markdown in the desk folder on your own computer, what each one holds, and which of them an update never touches.
lead: Everything the desk keeps for you is a plain file in the desk folder, readable in any text editor and by your AI agent. This page lists them, and says which an update never writes.
---

## In the data folder

| File | What it holds |
|---|---|
| `data/book.json` | Desk · Book: symbols from any market, shares, average cost, cash per currency. |
| `data/watchlist.json`, `data/watchlist_us.json`, `data/watchlist_global.json` | The three watch grids. Home codes are your broker's codes when it serves quotes, else the exchange's symbols, else Yahoo's. |
| `data/fno_watchlist.json` | The names for the home options tape, read by a broker file that serves chains. |
| `data/funds.json` | The 13F filers you follow, name and CIK. |
| `data/members.json` | The Congress members you track. |
| `data/supply_chain.json` | The starter value chain; your own chains live in the research vault. |
| `data/alerts.json` | The alert rules: day moves, margin, futures expiry, earnings, price levels, insider clusters, 13Ds, commodity moves. |
| `data/watch_levels.json` | Price levels per holding, optional. |
| `data/commodities.json` | The commodity board: fifty-four cards, their free sources, and the industries a rise squeezes and helps. |
| `data/exposure_us.json`, `data/exposure_<market>.json` | The listed names behind those industries for one market, with the raw-material share from filings. `exposure_example.json` is the template. |

## The research vault

One folder, wherever you put it (beside the desk, in Documents, or in a folder a drive syncs; Settings, under Where the vault lives). Inside: your notes as markdown, one folder per name for the files you bring in, `chains/` for your value-chain maps, `tasks.md`, the journal, and the drawings from the ticker page's chart. [Notes and the research vault](/docs/get-started/notes/).

## The settings file and the day's token

`.env` in the desk folder holds every key and setting the Settings screen writes. A broker that issues a session key each trading day keeps that day's key in a second small file beside it. [The settings file](/docs/reference/settings-file/).

## What an update never touches

`.env`, the day's token, `cache/`, `logs/`, `output/`, the virtual environment, and every file under `data/` that is yours. Three reference tables the desk ships (`commodities.json`, `exposure_us.json`, `exposure_example.json`) are refreshed only when your copy is byte-for-byte a shipped version; `alerts.json` is merged rule by rule so a threshold you tuned survives. When a version changes the shape of a file you own, the desk keeps a copy first and says so on the strip. [Getting a newer version](/docs/install/updates/).

## Back up

Settings, Your desk, Your files: one zip of everything above, without the keys. [Back up](/docs/install/back-up/).
