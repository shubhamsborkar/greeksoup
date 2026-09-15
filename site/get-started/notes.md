---
title: Notes, the research you write
nav: Notes
description: GreekSoup keeps your research notes as plain Markdown files in the desk folder, each one linked to the listings it names, the project it belongs to and the notes it links to.
lead: Fourteen screens read the record. Notes is where you write what you make of it, and the desk connects what you write to the names and the other notes it belongs with.
---

## What a note is

One plain text file in `data/notes`, one per note. The top of the file is the card: a title, a type (a general note, news, an insight, a call, a meeting, a risk, or a project), the listings it is about, the project it belongs to, and tags. The rest is the note itself, in Markdown. Open the folder in Obsidian or any editor and the same files are there, and an AI agent on your computer reads and writes them like any other file.

## How notes connect

Three things link a note to the rest of your research, and you get all three without doing anything extra:

- **Names.** A note lists the listings it is about, and writing `$AAPL` anywhere in the text names one too. Every note that names a listing shows on that listing's page, under **Your notes on AAPL**.
- **Projects.** A project is a note whose type is Project. The names it lists are the names in the project, and any note that says it belongs to the project shows under it. A project on, say, Gulf delivery connects the two or three names you are working through, and every call note and risk note you write about them.
- **Links.** `[[Another note]]` links to a note by its title. Both notes show the link, one as a link out, the other as linked from.

The page of any listing then shows one more line: the other names connected to it through your notes. Two companies that share a project, or sit in the same note, are connected, and that is how a note about a supplier turns up when you are looking at the customer.

## Writing one

On the Notes screen, **New note**. Type the company's name in the Names box and pick the listing from the list; the desk fills in the symbol. Give it a project by typing a project note's title, or leave that empty. Write. Save, or press the save shortcut. From any listing's page, **Note on AAPL** opens a new note with the name already filled in.

## The examples

A fresh desk arrives with one example project and two example notes, so the screen shows how the pieces fit. They are three files in `data/notes` whose names start with `example-`; delete them from the Notes screen or from the folder whenever you like.

## Your AI reads them

The Ask box on a listing's page sends your notes about that listing along with the screen's numbers, so the answer knows what you already think. On the Notes screen it sends the notes themselves. Nothing leaves your computer except that one question to your own AI key.
