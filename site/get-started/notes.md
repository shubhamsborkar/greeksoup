---
title: Notes, the research you write
nav: Notes
description: GreekSoup keeps your research notes as plain Markdown files in the desk folder, each one linked to the listings it names, the project it belongs to and the notes it links to.
lead: Fourteen screens read the record. Notes is where you write what you make of it, and the desk connects what you write to the names and the other notes it belongs with.
---

## What a note is

One plain text file in `data/notes`, one per note. The top of the file is the card, the rest is the note itself, in Markdown. Open the folder in Obsidian or any editor and the same files are there, and an AI agent on your computer reads and writes them like any other file.

The card answers three questions about a note:

- **What is it about?** A listing, a commodity, a sector, the macro picture, or nothing in particular. A note about a listing names the listing; a note about a commodity, a sector or a theme names that instead, so `Commodity · rubber` and `Sector · Gulf delivery` are subjects the desk groups on the way it groups on a name.
- **Which period?** The quarter or year the note is researching, written the way you say it: `Q2 FY26`, `H1 FY26`, `FY26`, `Q3 2026`. The desk tidies the spacing and the case and otherwise keeps your words, and the Notes screen filters on it, so everything you wrote on one quarter is one click.
- **What sort of note?** A general note, news, an insight, a call, a meeting, a risk, an answer your AI gave that you chose to keep, or a project.

Then the project it belongs to, and tags. Every field on the card is a property Obsidian reads, so its own filters and Bases work on the same fields.

## Why the folder stays flat

The folder stays flat on purpose. Links between notes resolve by title, so a note can change what it is about by editing one line on its card rather than moving a file, and nothing that links to it breaks. Obsidian filters on the card's fields, so "every commodity note" or "everything on Q2 FY26" is one filter with no folder to keep tidy. And an AI agent needs to know exactly one place to look.

## How notes connect

Three things link a note to the rest of your research, and you get all three without doing anything extra:

- **Names.** A note lists the listings it is about, and writing `$AAPL` anywhere in the text names one too. Every note that names a listing shows on that listing's page, under **Your notes on AAPL**.
- **Projects.** A project is a note whose type is Project. The names it lists are the names in the project, and any note that says it belongs to the project shows under it. A project on, say, Gulf delivery connects the two or three names you are working through, and every call note and risk note you write about them.
- **Links.** `[[Another note]]` links to a note by its title. Both notes show the link, one as a link out, the other as linked from.

The page of any listing then shows one more line: the other names connected to it through your notes. Two companies that share a project, or sit in the same note, are connected, and that is how a note about a supplier turns up when you are looking at the customer.

## Writing one

On the Notes screen, **New note**. Say what it is about; for a listing, type the company's name in the Names box and pick it from the list, and the desk fills in the symbol. Give it a period, a project by typing a project note's title, or leave those empty. Write. Save, or press the save shortcut. From any listing's page, **Note on AAPL** opens a new note with the name already filled in.

## Keeping an answer

Every answer in the Ask box has a **Save as note** button under it. Press it and a small card opens, already filled from the screen you asked on: the name on a listing's page, commodity on the Commodities screen, macro on Macro. Set the period, change the title if you like, Save. The question and the answer land in `data/notes` as a note of type AI answer, with the screen, the date and the model written at the foot, so you can see later where it came from. Nothing is saved unless you press the button; an answer you do not keep is gone when you close the box.

## The examples

A fresh desk arrives with one example project and three example notes (a call, a risk, and a commodity note with a period), so the screen shows how the pieces fit. They are four files in `data/notes` whose names start with `example-`; delete them from the Notes screen or from the folder whenever you like.

## Your AI reads them

The Ask box on a listing's page sends your notes about that listing along with the screen's numbers, so the answer knows what you already think. On Commodities it sends your commodity notes, on Macro your macro notes, and on the Notes screen the notes themselves. Nothing leaves your computer except that one question to your own AI key.
