---
title: Notes and the research vault
nav: Notes
description: GreekSoup keeps your research as plain files in the desk folder, the notes you write and the files you bring in, each one linked to the listings it names, the project it belongs to and the notes it links to.
lead: Fourteen screens read the record. The research vault is where you keep what you make of it, notes and files alike, and the desk connects everything in it to the names and the other notes it belongs with, so nothing you did six months ago is lost.
---

## The vault

Everything lives in the desk's own `data/research` folder, in plain files: `notes` holds one Markdown file per note, `files` holds what you bring in, an annual report, a model, a screenshot, one folder per subject (`files/AAPL`, `files/rubber`). Open the folder in Obsidian or any editor and the same files are there, an AI agent on your computer reads and writes them like any other file, and the backup on Settings takes the whole vault. Nothing is saved here unless you save it.

## What a note is

One plain text file in `data/research/notes`. The top of the file is the card, the rest is the note itself, in Markdown.

The card answers three questions about a note:

- **What is it about?** A listing, a commodity, a sector, the macro picture, or nothing in particular. A note about a listing names the listing; a note about a commodity, a sector or a theme names that instead, so `Commodity · rubber` and `Sector · Gulf delivery` are subjects the desk groups on the way it groups on a name.
- **Which period?** The quarter or year the note is researching, written the way you say it: `Q2 FY26`, `H1 FY26`, `FY26`, `Q3 2026`. The desk tidies the spacing and the case and otherwise keeps your words, and the Notes screen filters on it, so everything you wrote on one quarter is one click.
- **What sort of note?** A general note, news, an insight, a call, a meeting, a risk, an answer your AI gave that you chose to keep, a document, a model or a clipping (a note with a file attached), a decision or an exit, or a project.

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

## Files: a document is a note with a file attached

Drop an annual report on a note, or press **Attach a file** on a listing's page, and it becomes a note of type Document with the file attached. The file goes into `files/AAPL` when you save the note and nowhere else; the note carries the connections, so the report shows on Apple's page, takes the period FY25, joins a project, and links to the call note that quotes it. A spreadsheet makes a Model, a screenshot makes a Clipping, and you can change the type if the desk guessed wrong. Open the file from the note in a new tab; an image shows on the note itself.

The loop closes both ways. **Remove file** on a note asks whether the file stays in the vault or goes too. Deleting a note that has a file asks the same. A file that no note points at, dropped into the folder from Finder or left behind on purpose, is listed on the Notes screen under **In the vault, on no note yet**, with **give it a note** and **delete** beside it, so nothing brought in is ever hidden. A file you move away by hand shows as missing on its note rather than vanishing.

## The desk reads what is inside

When a file arrives the desk reads its text once, locally, into `data/research/index`: a PDF page by page, a spreadsheet sheet by sheet with its first rows, a Word file by paragraph, a presentation by slide. Nothing leaves your computer and the index is rebuilt from the files whenever it is missing, so it is never the record. From then on the search box on the Notes screen and Command K find a phrase that lives only inside an annual report, marked **in the file**, and the Ask box on that listing's page reads your notes and your documents about it along with the screen's numbers, so an answer can quote the filing you brought in. A scanned image has no text to read; the file is kept and opens as it is, and the note says so.

## Where a name stands

Every listing's page carries a status: **watchlist**, **researching**, **thesis built**, **invested**, **exited**. Two of the five the desk can see for itself and shows as such: a name in one of your books reads invested, a name on a watch grid reads watchlist. Pick one yourself and your word wins, dated, and every change is kept in `data/research/status.json`, so an exit six months on still shows when the thesis was built. The Notes screen filters on status, so "everything on the names I am researching" is one click.

## The timeline

Under your notes on a listing's page, and on the Notes screen when you are looking at one name, the **Timeline** lays out everything about that name by the period it belongs to, newest first, and by date inside each: the Q1 call note, the model built after it, the annual report, the day the status changed. It is the folder drawn on a time axis, and it is how the note from twelve months back is one glance away rather than lost.

## Keeping an answer

Every answer in the Ask box has a **Save as note** button under it. Press it and a small card opens, already filled from the screen you asked on: the name on a listing's page, commodity on the Commodities screen, macro on Macro. Set the period, change the title if you like, Save. The question and the answer land in the vault as a note of type AI answer, with the screen, the date and the model written at the foot, so you can see later where it came from. Nothing is saved unless you press the button; an answer you do not keep is gone when you close the box.

## The examples

A fresh desk arrives with one example project and three example notes (a call, a risk, and a commodity note with a period), so the screen shows how the pieces fit. They are four files in `data/research/notes` whose names start with `example-`; delete them from the Notes screen or from the folder whenever you like.

## Your AI reads them

The Ask box on a listing's page sends your notes and the text of your documents about that listing along with the screen's numbers, so the answer knows what you already think and what you have already read. On Commodities it sends your commodity notes and files, on Macro your macro ones, and on the Notes screen the notes themselves. Nothing leaves your computer except that one question to your own AI key.
