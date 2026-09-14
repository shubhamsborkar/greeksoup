---
title: What it talks to
nav: What it talks to
description: Every place GreekSoup sends a request, what it sends, and what it never sends. No telemetry, no account, no analytics.
lead: The desk runs on your computer and answers only to your computer. This is the whole list of places it reaches out to, so you can decide with your eyes open.
---

## The list

- **Your broker**, only if you connected one, with the keys you gave it, read-only. Each shipped broker file uses that broker's documented read endpoints and none of them can place an order.
- **The public record**: SEC EDGAR for filings, FINRA for short interest, CBOE for delayed option chains, FRED for macro series, the Senate and House disclosure sites for Congress trades, Yahoo Finance for quotes and history, Trading Economics for a few commodity benchmarks, and the India sources named on the Macro screen.
- **Your data provider**, only if you gave it a key. Financial Modeling Prep ships today.
- **Your AI**, only if you gave it a key or pointed the desk at a model running on your own computer.
- **GitHub**, once a day, one small request for the `VERSION` file, to know whether a newer version exists. The update itself downloads the desk's files from GitHub when you click the button.
- **Google Fonts**, for the desk's typefaces.

That is the list. Nothing else.

## What it never sends

Nothing about you, your book, your lists or your keys goes anywhere. There is no telemetry, no analytics, no crash reporting and no account. The daily version check carries no identifier; it is the same request a browser makes when it opens a page.

## Where your keys live

In one settings file inside the desk folder, written by the Settings screen and read when the desk starts. The update never touches it, the backup never includes it, and the page your AI app reads tells the AI not to read it either.

## The address

The desk answers at `http://localhost:8765`, which means "this computer" and nothing beyond it. It has no login of its own because nobody else can reach it. Do not point it at the internet; if you want it on another computer, install it there.

## If you want to check

The desk's own check prints every setting by name and never by value, plus which of the sources above it can reach from your computer. In the desk folder: `python doctor.py`. Give the printout to your agent or paste it into a bug report; nothing in it is private.
