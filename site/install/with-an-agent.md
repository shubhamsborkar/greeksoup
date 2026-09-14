---
title: Install with an AI agent
nav: With an AI agent
description: Have an AI coding agent install GreekSoup, connect your broker and fill in your keys for you.
lead: Use this path if you already have an agent, or if you want it to connect your broker and fill in your keys while you watch. About twenty minutes, most of it the agent working.
---

## The four steps

<ol class="steps" markdown="1">
<li markdown="1">
**Get the folder.** On the repository page on GitHub, click the green **Code** button and choose **Download ZIP**. The file lands in your Downloads folder. Double-click it and a folder with the same name appears next to it; drag that folder into Documents. That folder is the desk, and everything below happens inside it.
</li>
<li markdown="1">
**Get an agent, if you do not have one.** You do not need to know what a terminal is. Install the Claude desktop app from claude.ai/download (Codex, Kimi Code and Grok Build have their own apps and work the same way), sign in, and open its **Code** section. It asks which folder to work in: choose the desk folder you just moved to Documents. That is what "open the folder in your agent" means everywhere in these pages. If you already use Claude Code in a terminal, open a terminal, type `cd ` with the space, drag the desk folder onto the terminal window, press Enter, then type `claude` and press Enter.
</li>
<li markdown="1">
**Paste this and press Enter.**

```
Read README.md in this folder and set the desk up for me on this computer. Install what it needs, copy .env.example to .env, and ask me for each key one at a time, telling me where to get it. My broker is <your broker>. If it is not one of the six the desk ships, read its API documentation and write the broker file the way brokers/README.md describes. If I say I have no broker to connect yet, leave the broker empty. Then start the desk, set it to start by itself whenever I log in, and tell me the address to open.
```
</li>
<li markdown="1">
**Answer its questions.** It asks for your broker's keys and, if you want one, the feed key, and it tells you where each comes from. If you have neither, say so and it skips them. It then installs everything, starts the desk, and gives you an address. Open that address in your browser.
</li>
</ol>

## When something goes wrong, then or later

Give your agent the README. Whether you use Claude Code, Codex, Kimi Code, Grok Build or any other agent, point it at the desk folder, tell it to read `README.md`, and describe the problem in your own words: it cannot install, the page is blank, the broker will not connect, you want a screen changed. Copy any error you see and paste it in. That is the whole method, and it is the same one that built the desk.

## Changing the desk afterwards

Everything is a plain sentence to the agent. *Add Nvidia to my US watchlist. Follow Pershing Square on the Funds tab. Alert me when any holding moves five percent in a day. Add a tab that shows my dividend calendar.* Your lists also sit as plain text files in the `data` folder if you prefer to edit them yourself; each one has a comment at the top saying what goes in it.
