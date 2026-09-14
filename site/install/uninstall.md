---
title: Uninstall
description: Remove GreekSoup from your computer completely, in two steps.
lead: Two steps, and nothing is left behind. The desk installed nothing outside its own folder except the small start-at-login entry.
---

## Step one: switch the always-on service off

Double-click **Stop Desk** in the desk folder. That removes the start-at-login entry and stops the desk. On the Settings screen, switching *Start with the computer* off does the same.

By hand, if you prefer: on a Mac delete `~/Library/LaunchAgents/com.research-desk.plist`; on Windows delete the task "Research Desk" in Task Scheduler; on Linux `systemctl --user disable --now greeksoup-desk.service` and delete the unit file from `~/.config/systemd/user/`.

## Step two: delete the folder

Back up first if you want your lists ([Back up](/docs/install/back-up/)). Then delete the `GreekSoup` folder (or wherever you put it). Everything the desk had, its program, its environment, your settings file, your data, its caches and its logs, was inside that folder.

If the install put Python on your computer because it was missing, Python stays; it is a normal python.org or winget install and is removed the normal way if you want it gone.

## What the desk never touched

Nothing outside its folder and the one service entry: no other program, no system setting, no browser setting, no account anywhere. It never had an account of its own to close.
