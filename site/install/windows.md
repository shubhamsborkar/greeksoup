---
title: Install on Windows
nav: Windows
description: Install GreekSoup on Windows with one line in PowerShell.
lead: One line in PowerShell. Written from Microsoft's documented commands.
---

## The line

Press the Windows key, type `PowerShell`, press Enter, then paste this line and press Enter:

```
irm https://greeksoup.ai/install.ps1 | iex
```

If Python is not on your PC yet, the line installs it with winget and a window may ask you to approve. Everything else goes into a folder called `GreekSoup` in your user folder. When the line finishes, the desk is open in your browser at `http://localhost:8765` and it starts when you log on from then on, through a task in Task Scheduler.

!!! warning "An honest note"
    A fresh Windows machine runs this line on every change to the desk: install, every screen, the check, start at login and uninstall, all tested before a version ships. No administrator is needed; on a work or school PC that refuses a scheduled task, the desk uses a shortcut in your own Startup folder instead. If the line still complains on yours, paste the window's text to an AI agent and ask it to fix it; that is the same method that built the desk.

## Knobs, if you want them

Set either of these in the same PowerShell window before the line, and the install follows them.

| Knob | What it does |
|---|---|
| `$env:GREEKSOUP_HOME = "D:\Desk"` | Put the desk somewhere other than your user folder |
| `$env:GREEKSOUP_PORT = "8770"` | Answer on a different door number than 8765 |

## Running it again

The same line on a PC that already has the desk only starts it. It never overwrites your settings file or anything in your data folder.

## The files in the folder

Open the `GreekSoup` folder in File Explorer and you find a few files with plain names, ending in `.bat`. **Start Desk** starts the desk and keeps a small window open while it runs. **Keep Desk Running** sets it to start at logon and come back if it stops; the install already did this. **Stop Desk** switches that off. [Keep it running](/docs/install/keep-it-running/) explains them.
