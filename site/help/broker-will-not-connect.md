---
title: The broker will not connect
nav: Broker will not connect
description: What to do when a broker will not connect to GreekSoup: the Check button on Settings, keys pasted with a stray space, the read-only key kind, the daily login on ICICI Direct and Zerodha, a paper or sandbox account's own pair, and the button that hands the error to your AI.
lead: A broker connects on Settings with what it hands out from its own dashboard, and the Check button tells you in one line whether it did. This page is the short list of what stops it, in the order they happen.
---

## First, the Check button

Settings, Connect, next to the broker's name. It asks the broker for the account and prints what came back. A working broker says "connected as" and the account. A failing one says what the broker said, and beside the line is a button that hands that error, with the broker's name and the desk's README, to the AI you chose, which reads the broker's documentation and says what to change.

## The things that stop it

**A stray space or a missing character in a key.** Keys are pasted, and a copy from a web page can carry a space at either end. Remove the keys, paste each again, Check.

**The wrong key kind.** Each broker page says which key the desk wants. A paper account (Alpaca) or a sandbox (Tradier) has its own pair and its own switch on Settings; a live key with the paper switch on connects to nothing. Trading 212 wants a key generated in the app with the account scopes. Interactive Brokers wants a Flex Web Service token and a query id, not the gateway login. [Brokers](/docs/brokers/).

**The daily login.** ICICI Direct and Zerodha issue a session key each trading day. Until today's login, Desk · Home shows the last saved book with live marks and says the session is off. Settings has the box under the broker's keys: Open the broker login, sign in on the broker's page, and the desk takes the day's key from the page it returns to (by itself when the redirect address in your broker app points at the desk). That is the broker's rule, not a fault.

**The broker's site is down or slow.** Check says so with the broker's own words. Wait, then Check again.

**Two copies of the desk.** "The desk is already running" means another copy is on the same door number, and the one that opens may not be the one whose Settings you filled. Stop one, or give the second its own door number in its settings file.

## What it never is

The desk does not place orders and asks for no trading permission, so a connection that fails is never about that. A key with trading scope is not needed anywhere; where the broker offers a read-only kind, use it.

## Still nothing

Run the check, `python doctor.py` in the desk folder; it names which keys are set (never their values) and which sources it can reach. Give it to your agent or to Tell us in the sidebar, with the broker's name.
