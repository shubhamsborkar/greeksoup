---
title: Install on Linux
nav: Linux
description: Install GreekSoup on Linux with one line, kept running by a systemd user service.
lead: The same line as the Mac. Python has to be there already; the line tells you the package if it is not.
---

## The line

In a terminal:

```
curl -fsSL https://greeksoup.ai/install.sh | bash
```

Python 3.10 or newer is needed. If it is missing the line stops and says what to install: on Ubuntu or Debian `sudo apt install python3 python3-venv`, on Fedora `sudo dnf install python3`. Run the line again after that.

The desk goes into `~/GreekSoup`, with its own environment inside that folder. The line then writes a small systemd user service, `greeksoup-desk.service`, enables it and starts it, so the desk starts at every login and restarts by itself if it stops. It opens the address in your browser if a browser is there to open it.

## The knobs

The same three as on a Mac, set before `curl` on the same line: `GREEKSOUP_HOME` for the folder, `GREEKSOUP_PORT` for the door number, `GREEKSOUP_NO_SERVICE=1` to run it once without the service.

## The service, by hand

If you would rather write it yourself, this is the whole unit, at `~/.config/systemd/user/greeksoup-desk.service`:

```
[Unit]
Description=GreekSoup desk
[Service]
ExecStart=/home/you/GreekSoup/.venv/bin/python server.py
WorkingDirectory=/home/you/GreekSoup
Restart=always
RestartSec=5
[Install]
WantedBy=default.target
```

Then `systemctl --user daemon-reload` and `systemctl --user enable --now greeksoup-desk.service`. The switch on the Settings screen, *Start with the computer*, reads and writes this same unit.

## A headless machine

The desk answers only on the machine it runs on, at `127.0.0.1`. On a server with no screen, reach it through an SSH tunnel from your own computer: `ssh -L 8765:localhost:8765 you@server`, then open `http://localhost:8765` here. Nothing about the desk is exposed to the network by that.
