---
title: How to research a stock with AI without the numbers being made up
nav: AI without made-up numbers
description: A five-step method for researching a stock with an AI so that every number in the answer comes from the record rather than the model's memory, and how the GreekSoup desk is built around it.
lead: An AI asked "what is this company's operating margin" will give a number, and it will sound right. Whether it is right depends on where the number came from. This is the method that keeps the numbers honest, in any tool, and how the desk is built to make it the default.
---

## Why the numbers get made up

A language model answers from what it learned, and what it learned about a company is a blur of old filings, articles and forum posts. Ask it for a figure and it produces the most plausible one, which is what a language model is built to do. The trouble starts when that figure gets treated as a fact. The fix is to put the document in front of the model so that it reads instead of recalling.

## The method

**1. Put the record in front of it first.** Before any question, the filing, the statement, the holdings table or the price series has to be on the screen or in the prompt, with its source. Without that, the answer comes from memory.

**2. Ask about what it can see.** Ask "what does this table say about the margin trend" and the model reads the table. Ask "what is the margin" and it is free to remember one. The phrasing points the model at the page.

**3. Make it show its reading.** Ask which line, which filing, which date. If it read the page it can point to the line.

**4. Check one number against the primary source before acting.** Not every number, one. Open the filing on EDGAR, the exchange's page, the central bank's series, and match it. If that one is wrong, treat the whole answer as a draft.

**5. Write the note with the number and its source.** Three months on, a number with no source cannot be checked. A note that says "Q2 FY26 operating margin 14.2%, from the 10-Q filed 5 August 2026" can be checked next quarter and the one after.

## How the desk does this by default

GreekSoup was built around step one. Every screen is a page of the record with its source named beside each number: SEC EDGAR for the 13F and insider tables, CBOE for the options chain, FINRA for short interest, FRED for the macro series, the exchange's filings on a home-market name, your broker for your book.

The Ask box on every screen sends your question together with that screen's numbers, and only those, to whichever AI you chose. That is step two done for you: the AI is reading the page you are looking at. The brief it receives says to answer from the data and to say so when the screen does not answer the question rather than guess. The answer comes back with a line naming the addresses it read, which is step three. When a number in the answer looks wrong you have the screen it came from and the source the screen names, which is step four. Under any answer worth keeping sits **Save as note**, a plain file in your research vault linked to the name, which is step five.

The desk changes nothing on its own. Research mode, the default, reads and answers. Nothing is sent until you press Enter, and it goes to the one AI you picked, which can be a model on your own computer that sends nothing anywhere.

## What can still go wrong

- **The feed is wrong, late or restated.** The desk names the source so that the check in step four is one click. It does not make the source right.
- **The AI misreads a table.** It happens, more on dense pages. The addresses line and the source beside the number are there for that reason.
- **Thin names.** A company with few filings and little coverage has a thin record, and an AI will be tempted to fill it. On the desk the temptation shows up as a shorter answer; ask it what it could not find.
- **Your own question.** "Is this a buy" is not answered by any screen. The desk's AI is told to say so.

## Without the desk

The method works in a chat window too. Paste the filing text, ask about the pasted text, ask for the line it used, check one number, write the note. It is more typing, and the pasted text is gone when the chat is, which is the reason the desk keeps its screens and its notes as files.
