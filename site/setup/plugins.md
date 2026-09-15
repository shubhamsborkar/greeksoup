---
title: Plugins
nav: Plugins
description: A GreekSoup plugin is a folder that adds a screen to the sidebar, blocks a note can carry, or a door for the Ask box, such as the terminal door that answers through the coding agent already on your computer.
lead: The desk is the platform. A plugin is a small folder you bring in from Settings, and the first one lets the Ask box answer through the coding agent you already have, with no separate key.
---

## What a plugin is

A folder in `data/research/plugins`, with a `plugin.json` that says what it adds and the files that add it. Three kinds, each small:

- **A screen.** One HTML page in the sidebar, reading the desk's own addresses the way every screen does. Every address is listed at `/agent` on your desk.
- **Blocks.** A JavaScript file that gives a note a new block to carry: three backticks, `desk`, then the block's line. Two hooks make one: where its data comes from, and how it is drawn.
- **A door.** A way for the Ask box to talk to something on this computer. The door names a command; the desk hands it the same brief it would give a provider (your question, the screen's numbers, your notes) on standard input and shows what comes back on standard output.

A plugin runs on your computer and reads what you let it. Settings shows what each one adds and what it talks to before it goes in, and removes it in one click. Nothing is brought in on its own.

## The terminal door

The first plugin. Bring it in from Settings, under Plugins, and the Ask box gains a small picker at the top: your AI from Settings, or **Terminal**. Pick Terminal and the question goes to the coding agent already installed on your computer, Claude Code or Codex, whichever the desk finds, with the screen's numbers and your notes, and the answer comes back into the box, where Save as note and Save as task work as usual. No key on Settings is needed for this door; the agent reaches its own provider with its own login, and that is the one thing it talks to. The agent is told to answer from the data and nothing else: no commands, no file edits, no permissions.

## Hello, a plugin to copy

The second plugin is the smallest there is, here to be copied: one screen and one block. Bring it in, open Hello in the sidebar, then copy its folder, rename it in `plugin.json`, change what you like, and bring your folder in from Settings under From this computer. A zip works the same way.

## The list

Settings reads a list at greeksoup.ai of the plugins we publish: name, what it adds, who wrote it, what it talks to, and one click to bring it in. The list is a plain file; a plugin from anywhere else goes in from a folder or a zip the same way, and the desk says what it talks to before it does.
