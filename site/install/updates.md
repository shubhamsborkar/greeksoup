---
title: Getting a newer version
nav: Updates
description: How GreekSoup tells you a newer version exists and brings it in with one click, keeping your keys and your lists.
lead: The desk keeps growing, and it tells you itself. One click brings the new version in and nothing of yours moves.
---

## The strip

Once a day the desk looks at the page you downloaded it from. When a newer version exists, a strip appears at the top of every screen with the date and what changed, and one button, **Update the desk**. **Not now** hides the strip until the next version.

Click the button and the desk brings the new version in, then restarts by itself and the page reloads once it is back. It takes under a minute.

## What it keeps

- Your settings file with every key in it. Never written.
- Your research vault: notes, files, chains, lists, the journal, tasks, plugins. Never written by an update.
- Every list in your `data` folder, exactly as it is. A file you lack is added; the alert rules are merged so a threshold you tuned survives and only missing rules are appended.
- Any file your agent changed for you, a rewritten broker file say. It is kept as it is, and the strip names it so you can ask the agent to merge the changes.
- The daily broker login, the caches and the logs.

## When a version changes the shape of a file you own

Every file you own carries a format number: your chains, your lists, Desk · Book, your watchlists, your alert rules. A version that changes one of their shapes ships the step that brings the old shape up. At the next start the desk keeps a copy of each such file under `cache/previous`, brings the file up, and says so on the banner: which file, and where the copy is. Nothing is lost; the copy is yours to open. A file written by a newer desk than this one, which happens when two computers share a vault and one is behind, is left as it is and named on the banner, so you know to update this one.

## Without the click

Switch on *Newer versions* on the Settings screen. The desk then brings a new version in the day it appears and tells you what changed the next time you open it.

## A copy from before the strip

A copy from before 13 September 2026 does not have the strip yet, so bring it up to date once by hand. Download the ZIP again from the green **Code** button on the repository page, so the new folder sits in your Downloads folder, then open your existing desk folder in your agent and paste:

```
A newer version of this desk is in my Downloads folder, in the folder that came out of the ZIP. Update this desk from it: bring over every program file and every page, keep my .env and everything in my data folder exactly as they are, add any file in the new data folder that mine does not have, add any alert rule from its data/alerts.json that mine is missing, then restart the desk and tell me what is new.
```

That paste also works on any copy, at any time, if you would rather not use the strip. If you took the desk with git, `git pull` in the desk folder does the same, and the agent restarts it.

## What was added, newest first

The list lives in the `VERSION` file at the top of the repository, one line per release, and the [landing page](/#releases) reads it live.

## Going back

The desk keeps the files each update replaced, for the last three versions, inside its own folder. If a new version misbehaves, tell your agent "go back to the previous version of the desk", or in the desk folder type:

```
python updater.py rollback
```

Then start the desk. Your settings file, your lists and your caches are not part of a rollback; only the desk's own files move.
