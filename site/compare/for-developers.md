---
title: Is GreekSoup for developers?
nav: For developers?
description: No. GreekSoup is a free, open-source equity research desk for investors and analysts who do not write code. One pasted line installs it, the settings are a screen, and an AI agent makes any change. What a developer gets is listed too.
lead: No. It is for people who research stocks and hold positions. The question comes up because the desk is open source, lives on GitHub and is written in Python, which are the marks of a developer tool. Here is what that means in practice.
---

## The one paragraph

GreekSoup is installed by pasting one line into a terminal on a Mac, Windows or Linux computer; the line finds or installs Python for you. After that it is a set of screens in your browser. Every setting is a field on the Settings screen. Every list is edited on the screen it belongs to. Your broker connects with a key pasted into a box. Your AI connects the same way, or through an app you already pay for. Nobody who uses the desk needs to open a code file, and the people who built it use it that way every day. It is on GitHub because that is where open-source software lives and where updates come from, and it is in Python because that is what the AI agents that built it write best.

## What "no coding" covers

- **Installing**: [one line](/docs/install/), or ask an AI agent to do it for you.
- **Connecting a broker, a data provider, an AI**: Settings, first tab.
- **Your lists, your screens, your home market**: Settings and the Your list button on each screen.
- **Changing the desk**: open the folder in Claude Code, Codex, Gemini CLI or another AI agent and say what you want, or use the Build mode in the Ask box, which does the same from inside the desk. The README inside the folder is written for the agent as much as for you. That is how the desk was built.
- **Updates**: a strip appears when a newer version exists; one click brings it in and keeps your files.

## What a developer gets anyway

The desk is plain files in one folder. A broker is one file to [a written contract](/docs/brokers/another-broker/); a market is one file to [another](/docs/markets/your-own-market/); a data provider is a third. Plugins add a screen. The research vault is markdown. Nothing is compiled, nothing is hidden and the licence is MIT. A developer can read all of it in an afternoon and change any of it. The desk has that property whoever it was made for.
