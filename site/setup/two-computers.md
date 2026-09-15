---
title: Two computers
nav: Two computers
description: How the GreekSoup research vault reaches a second computer, or a colleague, with no service and no account, through a folder you already sync.
lead: The vault is one folder of plain files. Put it inside a drive you already sync and the desk on your other computer reads the same vault; no service of ours, no account, your own storage.
---

## Where the vault lives

Settings has a panel, **Where the vault lives**. By default the vault sits in `data/research` inside the desk folder. Type the path of a folder inside a drive you already sync, iCloud Drive, Google Drive, Dropbox, OneDrive, Syncthing, and press **Move the vault there**. The desk moves the notes, the files, the journal, the tasks, the statuses and the plugins to that folder and reads from it from then on; the choice is kept in the settings file, so it holds after a restart. **Bring it back into the desk folder** is the way back.

## The second computer

Install the desk there, open Settings, and point **Where the vault lives** at the same folder once the drive has brought it across. The desk finds a vault already in that folder, adopts it, and folds its own in: a file the folder lacks moves across, an identical file is dropped, and a file that differs (the desk's own example notes, say, changed on one side) stays as the folder has it while the local copy is kept aside under `cache/previous`, so nothing is lost either way. From then on both desks read and write the same vault, and the drive carries every change.

## What to know

- Open the desk on one computer at a time for the smoothest result. Two desks writing the same file in the same minute are settled by the drive's own conflict rule, which usually keeps both copies with one renamed; the desk reads both.
- The text the desk reads out of your files lives in `index/` inside the vault and is rebuilt wherever the vault lands, so it is never the thing you are waiting on.
- Keys never travel this way. They stay in the settings file inside each desk folder, on purpose.
- A backup from Settings carries the vault wherever it lives, and a restore puts it back there.

Sharing a vault with a colleague is the same folder shared the way the drive shares folders; each of you runs your own desk on it.
