---
title: "The free feed is resting, or \"retry in a few minutes\""
nav: The feed is resting
description: Why a GreekSoup screen says the free feed is resting or asks you to retry in a few minutes, what Yahoo's rate limit does to a fresh desk, which screens it touches, what the desk does on its own, and what to do if it lasts.
lead: Quotes and charts on the desk come from Yahoo's free feed, which has no contract behind it and rate-limits an address that asks too often. A fresh desk asks for everything at once, so the first few page loads can show this. The desk backs off and retries by itself.
---

## What you see

- **"retry in a few minutes"** on a watch grid or a ticker page.
- **An amber line on a ticker page**: "The free feed is resting, so this is the page as read at 14:01. It refreshes on its own once the feed answers again."
- **The economic calendar panel on Macro** with a note instead of rows.
- A chart that shows the last read it has rather than today's bars.

## What is happening

Yahoo's endpoints answer "too many requests" to an address that asked for too much in a short window. The desk caches what it read, shows the last read with the time it was read, backs off, and asks again on a timer. Nothing is lost; the page refreshes on its own when the feed answers. On a fresh install the first Capitol build and the first commodity board are the heaviest asks, and both are once.

Some of Yahoo's endpoints refuse an address for days while the others answer. The calendar endpoint is one; when it refuses, the economic calendar fills from the public record instead (the BLS schedule, the Fed's meeting calendar, Forex Factory's weekly file) and the panel names which one answered.

## What to do

1. Nothing, for ten minutes. Most of it clears on its own.
2. Do not reload repeatedly; each reload is another burst.
3. If a grid stays empty for an hour, run the check: `python doctor.py` in the desk folder says which sources it can reach. Give the printout to your agent or to Tell us.
4. If you want a contract behind your prices: a connected broker prices the names it knows, and a data provider key adds the statements and longer history. [Data providers](/docs/setup/data-providers/).

## What it never means

It is not a fault in your keys, your broker or your install, and it is not the desk sending anything anywhere. [What it talks to](/docs/install/what-it-talks-to/) lists every address; Yahoo's is one of them.
