---
title: Install on a Mac
nav: Mac
description: Install GreekSoup on a Mac with one line in Terminal.
lead: One line in Terminal. About a minute, most of it the download.
---

## The line

Press Command and Space together, type `Terminal`, press Enter; a plain window opens. Paste this line into it and press Enter:

```
curl -fsSL https://greeksoup.ai/install.sh | bash
```

If Python is not on your Mac yet, the line installs it from python.org and your Mac asks for your password once. Everything else goes into a folder called `GreekSoup` in your home folder. When the line finishes, the desk is open in your browser at `http://localhost:8765` and it starts with your Mac from then on.

## What you see

The window prints each step as it goes: Python found, the download, what it installs, and at the end the address, the folder, and two reminders: keys are optional and go on the Settings screen, and newer versions arrive through the strip inside the desk.

## Knobs, if you want them

Set any of these on the same line, before `curl`, and the install follows them.

| Knob | What it does |
|---|---|
| `GREEKSOUP_HOME=/some/folder` | Put the desk somewhere other than `~/GreekSoup` |
| `GREEKSOUP_PORT=8770` | Answer on a different door number than 8765 |
| `GREEKSOUP_NO_SERVICE=1` | Start the desk for this run only, without setting it to start at login |

For example:

```
GREEKSOUP_PORT=8770 curl -fsSL https://greeksoup.ai/install.sh | bash
```

## Running it again

The same line on a computer that already has the desk only starts it. It never overwrites your settings file or anything in your data folder.

!!! note "If the address does not open"
    Give it a minute, then open the address in a fresh tab. If it stays blank, [the page is blank](/docs/install/the-page-is-blank/) has the steps, and the file `logs/desk-service.log` inside the desk folder says what happened.
