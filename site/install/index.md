---
title: Install
nav: Overview
description: The ways to install GreekSoup on a Mac, Windows or Linux computer: one line in a terminal, with an AI agent, or from source.
lead: One line is enough on any of the three systems. The other two paths are there for a reader who has an agent, or who wants to see every step.
---

## Pick your path

<div class="cards" markdown="0">
<a href="/docs/install/mac/"><b>Mac</b><span>One line in Terminal. Finds or installs Python, downloads the desk into a GreekSoup folder in your home folder, starts it, opens it.</span><em>About a minute</em></a>
<a href="/docs/install/windows/"><b>Windows</b><span>One line in PowerShell, written from Microsoft's documented commands.</span><em>About a minute</em></a>
<a href="/docs/install/linux/"><b>Linux</b><span>The same line as the Mac, with a systemd user service to keep it running.</span><em>About a minute</em></a>
<a href="/docs/install/with-an-agent/"><b>With an AI agent</b><span>Download the folder, open it in Claude Code, Codex, Kimi Code or Grok Build, paste one instruction.</span><em>About twenty minutes</em></a>
<a href="/docs/install/from-source/"><b>From source</b><span>Clone, make an environment, install what it needs, run the server.</span><em>By hand</em></a>
</div>

## What the one-line install does, in order

1. Finds Python on your computer, and installs it if it is missing (from python.org on a Mac, with winget on Windows; on Linux it tells you the package to install).
2. Downloads the desk into a folder called `GreekSoup` in your home folder.
3. Installs what the desk needs into that folder and nothing else on your computer.
4. Copies the settings file into place, empty. Keys come later, on the Settings screen.
5. Sets the desk to start with your computer and to come back by itself if it stops.
6. Starts it and opens it in your browser at `http://localhost:8765`.

Run the same line again later and it only starts the desk; new versions arrive through [the strip inside the desk](/docs/install/updates/).

## After the install

- [Keep it running](/docs/install/keep-it-running/): what the always-on service is and the two files that switch it.
- [Updates](/docs/install/updates/): the strip, the one click, and what it keeps.
- [Back up](/docs/install/back-up/): one zip of everything that is yours.
- [Uninstall](/docs/install/uninstall/): two steps, nothing left behind.
- [The page is blank](/docs/install/the-page-is-blank/): the four things to try, in order.
