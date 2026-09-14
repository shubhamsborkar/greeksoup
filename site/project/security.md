---
title: Security
nav: Security
description: How GreekSoup keeps your keys on your computer, what it talks to, and how to report a security problem privately.
lead: The desk answers only to your own computer, keeps your keys in one file it never sends, and places no orders. Here is how to report anything that looks otherwise.
---

## The shape of it

- The desk listens at an address only your computer can reach. It has no login because nobody else can get to it.
- Your keys live in one settings file inside the desk folder. The update never touches it, the backup never includes it, and the page your AI app reads tells the AI not to read it.
- The Settings screen accepts changes only from a browser on the same computer, which is the guard against a web page elsewhere posting to it.
- There is no order path, on any broker.
- [What it talks to](/docs/install/what-it-talks-to/) is the complete list of outbound requests. No telemetry, no analytics, no account.

## Reporting a problem

Open a GitHub issue titled `Security` with no details in it, and we will reply with a private channel within a few days. Please do not post the details publicly first. The repository's `SECURITY.md` says the same.

## Keeping your copy safe

- Do not expose the port to the internet.
- Back up from Settings before a big change.
- Every number comes from a feed that can be wrong, late or restated. Verify against the primary source before acting on anything.
