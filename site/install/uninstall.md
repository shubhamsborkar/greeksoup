---
title: Uninstall
description: Remove GreekSoup from your computer completely: one file to double-click, or one line, and nothing is left behind.
lead: One double-click, and nothing is left behind. The desk installed nothing outside its own folder except the small start-at-login entry, and the uninstall removes both.
---

## On a Mac or Linux

Double-click **Uninstall Desk.command** in the desk folder, or paste this in a terminal:

```
curl -fsSL https://greeksoup.ai/uninstall.sh | bash
```

## On Windows

Double-click **Uninstall Desk.bat** in the desk folder.

## What it does, in order

1. Stops the desk and removes the start-at-login entry.
2. Saves a copy of your lists and data to your Desktop, as `GreekSoup-backup-<date>.zip`. Your keys are not in it.
3. Asks whether to delete the folder too. Say yes and the desk is gone; say no and the folder stays for you to delete whenever you like.

Python stays on your computer. It was installed for you if you did not have it, and it is yours.

## By hand, if you prefer

Switch the always-on service off with **Stop Desk**, then delete the `GreekSoup` folder in your home folder. On a Mac the start-at-login entry is `~/Library/LaunchAgents/com.research-desk.plist`; on Linux it is `~/.config/systemd/user/greeksoup-desk.service`; on Windows it is the scheduled task named "Research Desk". Stop Desk removes it on all three.
