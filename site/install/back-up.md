---
title: Back up
description: One zip of everything on the GreekSoup desk that is yours.
lead: Everything that is yours sits in one folder, and Settings makes a zip of it with one click.
---

## The one click

Open Settings, scroll to **Your files**. It lists every file in your `data` folder with a plain name and its size, and a button, **Back up**, downloads one zip of that folder: your watchlists, the hand-kept book, the US book, the funds you follow, the members you track, the alert rules, the price levels, the value-chain map, the commodity map, your investing profile, and the whole research vault (`data/research`: notes, files, the journal, the tasks, the statuses, and any plugins you brought in).

The zip never contains your settings file with the keys in it, the daily broker login, or the downloaded caches. Those are either secret or rebuilt.

## Putting it back

Next to **Back up** sits **Restore a backup**. Pick the zip and the desk writes its files back into place, on this copy or on a fresh one on another computer. A file the restore would change is kept aside first under `cache/previous/restore-<date>`, so a restore can itself be undone, and the message afterwards says how many files were written, how many were already the same, and where the changed ones were kept. Keys are re-entered on the Settings screen of the new copy; that is the one thing the zip does not carry, on purpose.

That is also the way to carry the vault to a second computer today: back up here, restore there.

## By hand

The `data` folder is plain text files you can copy anywhere. The settings file, `.env`, is the other thing worth keeping if you would rather not type the keys again; keep it somewhere private.
