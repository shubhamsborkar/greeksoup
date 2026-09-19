---
title: Get started
nav: Overview
description: What GreekSoup is, what you need, and the three ways to get it running on your own computer.
lead: The desk runs on your computer, opens in your browser, and reads the public record plus whatever you choose to connect. Here is what you need and the three ways in.
---

## What you need

- A computer you leave on while you work. Mac, Windows or Linux.
- Nothing else, to begin with. Keys are optional, and every one of them is added later on the Settings screen inside the desk.

Optional, whenever you want them:

- **A broker account that lets a program read it**, which brokers call an API. Six connect as the desk comes: Alpaca, ICICI Direct, Interactive Brokers, Tradier, Trading 212 and Zerodha. Without one, you keep your holdings by hand on Desk · Book, and everything else still works.
- **A data feed key** from Financial Modeling Prep, for the parsed financial statements on the ticker page.
- **An AI coding agent** (Claude Code, Codex, Kimi Code or Grok Build). It can do the install for you, and it is how you change the desk later by describing what you want.

## Three ways in

<div class="cards" markdown="0">
<a href="/docs/install/mac/"><b>One line in a terminal</b><span>Paste one line, press Enter, and the desk is running and open in your browser about a minute later. Mac, Windows and Linux.</span><em>Most readers</em></a>
<a href="/docs/install/with-an-agent/"><b>With an AI agent</b><span>Download the folder, open it in your agent, paste one instruction. The agent installs it and asks for your keys one at a time.</span><em>About twenty minutes</em></a>
<a href="/docs/install/from-source/"><b>From source</b><span>Clone the repository, make an environment, run the server. For a reader who wants to see every step.</span><em>By hand</em></a>
</div>

## Where it lives

The desk opens at `http://localhost:8765`. "localhost" means *this computer*: the address is not a website, it is your own machine talking to itself, so nobody else on the internet can open it, and the parts already loaded work with no internet at all. `8765` is the door number the desk answers on. Bookmark that address.

## What happens next

Once it is running, [the first ten minutes](/docs/get-started/first-ten-minutes/) walk you through the screens that work with nothing added, and [the screens](/docs/get-started/the-screens/) name every one of the sixteen. When you are ready, [connect your broker](/docs/brokers/) and Desk · Home fills.
