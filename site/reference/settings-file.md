---
title: The settings file
nav: Settings file
description: Every line the GreekSoup Settings screen writes to the .env file in the desk folder, by name, with what each one does, so a reader or an AI agent can read or set one directly.
lead: The Settings screen writes one file, `.env`, in the desk folder. Nothing in it is required. This is every line by name, for a reader who would rather read the file than the screen, and for the agent that sets one on your behalf.
---

## The desk

| Line | What it does |
|---|---|
| `DESK_PORT` | The door number the desk answers on. `8765` unless you run two copies. |
| `HOME_MARKET` | Your country, as a two-letter code, when no broker sets it. |
| `SCREENS` | Screens you hid, as `chain:off,short:off`. |
| `RISK_BENCHMARK`, `RISK_BENCHMARK_LABEL` | The index Risk measures the home book against, and its name. |
| `JOURNAL` | Whether the desk writes its daily journal: `ask`, `always` or `never`. |
| `EDGAR_CONTACT` | The e-mail the SEC asks for with each request to EDGAR. Yours, set once. |

## Your broker

Each broker file names its own keys, listed in `brokers/README.md`; the ones that ship are `ALPACA_KEY`, `ALPACA_SECRET`, `ALPACA_PAPER`; `BREEZE_API_KEY`, `BREEZE_API_SECRET` (ICICI Direct); `IBKR_FLEX_TOKEN`, `IBKR_FLEX_QUERY`; `TRADIER_TOKEN`, `TRADIER_ACCOUNT`, `TRADIER_SANDBOX`; `T212_KEY`, `T212_SECRET`, `T212_DEMO`; `KITE_API_KEY`, `KITE_API_SECRET` (Zerodha). `BROKER` names the one on Desk · Home, `BROKERS` the list when more than one is connected. A broker with a daily session keeps the day's key in its own small file beside `.env`.

## Your data provider

| Line | What it does |
|---|---|
| `FMP_API_KEY` | The Financial Modeling Prep key, the provider that ships. |
| `DATA_PROVIDER`, `DATA_API_KEY`, `DATA_BASE_URL` | Another provider written to [the contract](/docs/reference/contracts/): its name, its key, where it answers. |

## Your AI

| Line | What it does |
|---|---|
| `AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY` | The lab, the model and the key from Settings, Your AI. |
| `AI_BASE_URL`, `AI_FORMAT` | For Any other endpoint: where it answers and how it is spoken to. |
| `AI_DOOR` | The app on this computer that answers the Ask box (Claude Code, Codex and the rest) when you chose one instead of a key. |

## Updates and plugins

| Line | What it does |
|---|---|
| `DESK_AUTO_UPDATE` | `on` applies a newer version without the click. |
| `DESK_UPDATE_VERSION_URL`, `DESK_UPDATE_ZIP_URL` | Point a fork or a private mirror at its own version file and zip. |
| `PLUGIN_LIST_URL` | Where the Plugins tab reads its list. |

The file is never carried by an update or a backup, and the page your AI agent reads tells it not to read it. [What it talks to](/docs/install/what-it-talks-to/).
