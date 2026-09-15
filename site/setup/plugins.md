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

The first plugin, and the one behind **Use it for Ask** under Your AI: when you pick Claude Code, Codex, Gemini CLI, Kimi Code, Grok Build, Qwen Code or Cursor there, the desk brings this door in for you. The Ask box gains a picker at the top naming each app found on this computer and what it runs on; the question goes to the app you picked with the screen's numbers and your notes, and the answer comes back into the box, where Save as note and Save as task work as usual. No key on Settings is needed; the app reaches its own provider with its own login, which the desk never sees. The app is told to answer from the data and nothing else: no commands, no file edits, no permissions; its own permission settings apply on top. [Your AI](/docs/setup/your-ai/).

## What a plugin can reach

A plugin's screen runs inside the desk and can read every address the desk answers, your book included, and write what the desk's own screens can write: a note, a list row, a chain. A door runs the one command it names. That is the desk's own reach, handed to code you chose to install, so treat a plugin you did not write the way you treat any program: read it first, or ask your agent to read it and say what it does. Settings shows what each one adds and what it talks to before it goes in, and removes it in one click. [Security](/docs/project/security/).

## Hello, a plugin to copy

The second plugin is the smallest there is, here to be copied: one screen and one block. Bring it in, open Hello in the sidebar, then copy its folder, rename it in `plugin.json`, change what you like, and bring your folder in from Settings under From this computer. A zip works the same way.

## The list

Settings reads a list at greeksoup.ai of the plugins we publish: name, what it adds, who wrote it, what it talks to, and one click to bring it in. The list is a plain file; a plugin from anywhere else goes in from a folder or a zip the same way, and the desk says what it talks to before it does.
