---
title: Install from source
nav: From source
description: Set GreekSoup up by hand from a clone of the repository.
lead: For the reader who wants to see every step. Five lines, then the same desk.
---

## The five lines

```
git clone https://github.com/shubhamsborkar/one-person-equity-research-desk.git
cd one-person-equity-research-desk
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then start it:

```
python server.py
```

and open `http://localhost:8765`. Close the window and the desk stops; [keep it running](/docs/install/keep-it-running/) makes it always on.

On Windows the environment line is `python -m venv .venv` followed by `.venv\Scripts\activate`, and the copy line is `copy .env.example .env`.

## Keys

Keys go on the Settings screen once the desk is up. The page writes the `.env` file for you, only the lines it knows, one each, comments kept, and it never shows a key back, only its last four characters. You can also edit `.env` yourself; it is a plain text file with a comment above every line.

## How the folder is organised

- `server.py` is the desk: it draws every screen and answers every address.
- `web/` holds the pages, one file per screen, and `web/assets/` the shared sidebar, theme and command palette.
- `brokers/` holds one file per broker and the contract for writing another. `markets/` holds one file per home market and its contract.
- `data/` holds the files that are yours: watchlists, the hand-kept book, the funds you follow, the alert rules, the commodity map. Every one has a comment at the top.
- `data_providers/` holds the contract for a data feed other than the one that ships.
- `cache/` and `logs/` are the desk's own and safe to delete; it rebuilds them.

The technical notes in the repository, `TECHNICAL.md`, go deeper: the data sources, how the update works, the always-on service on each system.

## Taking a newer version

`git pull` in the folder, then restart the desk. Or leave the strip inside the desk to do it; it works on a clone too, and it keeps any file you changed and names it so you can merge.
