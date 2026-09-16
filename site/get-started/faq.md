---
title: Questions readers ask
nav: FAQ
description: The questions readers ask about GreekSoup before and after installing it, answered plainly.
lead: The questions we get, in the order people ask them.
---

## Before you install

**Does it cost anything?**
No. GreekSoup is open source under the MIT licence. You bring your own keys, and without any key at all thirteen of the fifteen screens run on the free public record.

**Do I need a broker?**
No. Desk · Book takes a portfolio you keep by hand, in any market, and every intelligence screen reads the public record. A broker lights up Desk · Home and Watch · Home with your live account.

**Do I need a data key?**
No. A data key adds six years of statements, ratio history, estimates, peers and a DCF sandbox on the ticker page, the 50 and 200 day columns on the US watch grid, and a market-wide insider scan. Everything else runs without it.

**Which brokers connect?**
Alpaca, ICICI Direct, Interactive Brokers, Tradier, Trading 212 and Zerodha, read-only, as the desk comes. Any other broker that lets a program read your account is one file an AI agent writes to [the written contract](/docs/brokers/another-broker/).

**Which markets?**
Every country is on the Home market list in Settings. India and the United States carry the full public record (the results calendar, the filings, the market's own macro cards); about fifty more get their quotes, session hours and index from the free feed; every other country keeps its currency and measures Risk against the world index. A connected broker sets the country for you, and the deeper record for any market is one short file to a written contract. Global takes any symbol from any exchange.

**What does it run on?**
Mac, Windows and Linux. It needs Python 3.10 or newer, which the one-line install finds or installs for you, and a browser. We build and use it on a Mac; the Windows install line was written from Microsoft's documented commands and we would like to hear how it goes on your PC.

**Does it place orders?**
No. This copy reads your broker account and places no orders. There is no order path in the code. If you extend it to trade, that is your own build, under your broker's and your regulator's rules.

## After you install

**Where do my keys live?**
In one settings file inside the GreekSoup folder on your own computer, written by the Settings screen. [What it talks to](/docs/install/what-it-talks-to/) lists every place the desk sends a request.

**Does it send anything anywhere?**
Your broker, the public sources, your data provider and your AI if you connected them, and GitHub once a day to check for a newer version. No telemetry, no analytics, no account.

**Which AI can it use?**
Any. An app you already pay for on this computer (Claude Code, Codex, Gemini CLI, Kimi Code, Grok Build, Qwen Code, Cursor) answers with no key at all; fourteen providers are preset for a key, models running on your own computer among them; and any AI app on your computer can read the desk through [a page made for it](/docs/setup/your-ai/).

**Will using Claude Code or Codex from the desk put my account at risk?**
No. The desk never sees your login: it runs the maker's own app on your computer, the way a shell script would, hands it a question and reads the answer. That is the app being used as the app, under your own sign-in, which each maker documents. What the makers do decide is how the usage is counted; as of 15 June 2026 Anthropic counts Claude Code's print mode against your normal subscription limits and has paused a plan to move it to a separate monthly credit. If a maker changes its rules, switch the Ask box to a key or a local model and nothing else changes. [Your AI](/docs/setup/your-ai/) has the detail.

**Does my book go to the AI?**
When you ask, yes. The Ask box sends your question with the numbers on the screen you are on, and on Desk · Home those are your holdings. It goes to the one place you chose and nowhere else; a model running on your computer keeps it on your computer. Nothing is sent until you press Enter. [Security](/docs/project/security/).

**Can a web page I visit read my desk?**
No. Every request must name this computer as its host and, from a browser, must come from the desk's own pages; anything else is refused before it is read. [Security](/docs/project/security/) explains both guards.

**The lists on the screens are someone else's. Can I change them?**
Every list is yours. Funds, Capitol, Macro, Commodities and the options tape carry a Your list button: add, edit, remove with Undo, bring the starters back. Chain is yours to draft and build. [Your lists](/docs/setup/your-lists/).

**What happens to my files when the desk updates?**
Nothing is lost. Your keys, your lists, your research vault and any file your agent changed stay as they are. When a version changes the shape of a file you own, the desk keeps a copy first, brings the file up, and says so on the banner. [Updates](/docs/install/updates/).

**Can I open it on my phone or another computer?**
The desk answers only on the computer it runs on. That is a choice, so that it needs no login. Install it on the computer you want to read it on.

**Can I run it on a server? Is that safer?**
It runs wherever Python runs, but a server is the less safe place for this desk. Its safety rests on nothing else being able to reach it, which holds on a laptop and turns around on a machine with a front door on the internet. If you must, put it behind a reverse proxy with encryption and a login of your own; we do not document or test that path. [Your computer or a server](/docs/install/your-computer-or-a-server/).

**How do I change it?**
Open the folder in an AI agent, Claude Code, Codex, Kimi Code, Grok Build or whichever you use, and describe what you want. That is how the desk was built, and the README inside the folder is written for the agent as much as for you.

**How do updates work?**
Once a day the desk looks at GitHub. When a newer version exists, a strip appears with the date and what changed, and one click brings it in. Your keys, your lists and any file your agent changed stay as they are. [Updates](/docs/install/updates/).

**Can I go back to the previous version?**
Yes. The desk keeps the files each update replaced. Tell your agent "go back to the previous version of the desk", or type `python updater.py rollback` in the desk folder.

**How do I uninstall it?**
Double-click **Uninstall Desk** in the desk folder. It stops the desk, removes the start-at-login entry, saves your lists to the Desktop and asks before deleting the folder. [Uninstall](/docs/install/uninstall/).

**A number looks wrong.**
Every number comes from a feed that can be wrong, late or restated, and the source is named on the screen. Check it against the primary source before acting. If the desk itself misread something, [tell us](https://github.com/shubhamsborkar/greeksoup/issues/new/choose) with the screen and the symbol.
