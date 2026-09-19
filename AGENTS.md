# For the AI agent working in this folder

You have been opened inside a copy of GreekSoup, the one-person equity research desk. The person who opened you is an investor, usually with no engineering background, and this folder is their own desk. Read this before you change anything.

## What this is

A small Python program (`server.py` and the modules beside it) that serves sixteen research screens from `web/` at `http://localhost:8765` (the port is `DESK_PORT` in `.env` when it is not 8765). It reads the public record, the reader's broker if one is connected, and one optional data feed. It is read-only against every account: **there is no order path and you must not add one.**

While the desk is running, `http://localhost:8765/agent` lists every screen and the JSON address behind it, plus how this reader invests, in words they wrote themselves. Read it first when the question is about their book, a screen or a number; it is the same page the desk's own Ask box reads.

## What is theirs and what is the desk's

- **Theirs, never overwritten without being asked:** `.env` (their keys; never print a value, never commit it), `data/` (their positions, watchlists, alert rules and lists; the shipped starters live beside their rows), `data/research/` (their notes, chains, journal, files and lists: this is their research vault and nothing in it is written unless they ask), `data/book.json` and `data/profile.json`.
- **The desk's, replaced by every update:** every `.py` at the root, `web/`, `brokers/`, `markets/`, `data_providers/`, `plugins/`, `scripts/`, `VERSION`, `MANIFEST.json`. A file here that you change is kept by the updater (its hash no longer matches a shipped version), named in the update report, and the reader is told to ask you to merge it. So prefer a new file to an edited one where a contract allows it (a broker, a market, a data provider, a plugin), and say so when you edit a shipped file.
- **Never written by anyone:** `cache/`, `logs/`, `output/`, `.venv/`, `session_token*.txt`.

## How to do the usual things

- **Start or restart the desk:** `python server.py` in this folder, with the folder's own `.venv` active, runs it in the foreground. If the reader installed it to start with the computer, the service restarts it on its own within seconds of it stopping; `Stop Desk` and `Keep Desk Running` (`.command` on a Mac, `.bat` on Windows) are the switches, and `TECHNICAL.md` explains the service on each system.
- **Check the desk:** `python doctor.py` prints the Python version, whether the desk answers, which keys are set by name and never by value, the last error lines and which sources it can reach. Nothing in it is private; it is what a bug report needs.
- **Run the checks:** `python -m pytest tests -q`. They test the contracts, never the network.
- **Add a broker, a market or a data provider:** one file to a written contract, `brokers/README.md`, `markets/README.md`, `data_providers/CONTRACT.md`. Settings lists what the desk then knows about.
- **Go back a version:** `python updater.py rollback` keeps the last three.
- **Ship a change back to the project:** `CONTRIBUTING.md`.

## How to speak

Anything the reader sees, on a screen, in a message, in a file they open, is plain words for an investor: no engineering terms, no file paths, no jargon. Describe what a number shows and never say buy, sell or hold. Every figure on the desk names its source on the screen it came from; quote the source when you use one. When something refuses (a source, a broker, a key), say so in one sentence and carry on.

## The whole picture

`README.md` is written for the reader and says what every screen does. `TECHNICAL.md` is the file map, the data sources and the always-on service. `SECURITY.md` is what the desk talks to and the two guards on every request. The docs are at https://greeksoup.ai/docs/ and the project page at https://greeksoup.ai; both live in their own repository, gitlab.com/shikshan-nivesh/greeksoup-web (a checkout next to this one), so a release that adds or changes a feature edits the page there and runs its `build.py`, never a file here.
