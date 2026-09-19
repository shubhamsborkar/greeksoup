---
title: If something is wrong
nav: If something is wrong
description: Symptom first. What each thing a GreekSoup screen can do means, and the one check that tells your agent what to fix.
lead: Find what you are seeing in the list. Most of it is one step, and the last section is the check that hands the rest to your agent.
---

## The one check

In the desk folder, open a terminal and type:

```
python doctor.py
```

It prints your Python version, whether the desk is answering, which keys are set (by name, never by value), whether the start-at-login entry is there, the last error lines from the log, and which sources it can reach. Nothing in it is private. Copy the printout and give it to your agent with "read README.md in this folder, then fix what the check found", or paste it into [a bug report](https://github.com/shubhamsborkar/greeksoup/issues/new/choose).

If you would rather not open a terminal, tell your agent: "run the check in this folder and fix what it finds."

## What you see, and what it means

- **The address does not open.** The desk is not running. [The page is blank](/docs/install/the-page-is-blank/) has the four things to try, in order.
- **A screen is blank or a number looks off.** Reload once. Screens rebuild on their own within a few minutes; the free quote feeds sometimes ask a new desk to wait, and the desk retries by itself.
- **"retry in a few minutes" on a fresh install.** Yahoo rate-limits bursts of quotes. It clears on its own.
- **A broker screen says the session is off.** That is the broker's daily login, not a fault. [The broker's page](/docs/brokers/) says what to do, and the Settings screen has the box for today's token.
- **"The desk is already running."** Another copy is on the same port. Open the address; it is that copy. To run two, give the second one another port in its settings file.
- **A Mac says the file "cannot be opened because it is from an unidentified developer."** Right-click the file, choose Open, then Open again. Once is enough.
- **Windows asks about running scripts.** The one-line install runs in PowerShell as Microsoft documents it. If a policy blocks it, the [with an agent](/docs/install/with-an-agent/) path needs no script at all.
- **Windows antivirus says a file in the desk is "infected".** A false alarm on the install script, which downloads and runs things the way every installer does. Let it restart if it asks, then click **Update the desk** once more. [Antivirus on Windows](/docs/install/windows/#if-your-antivirus-speaks-up) has the whole of it.
- **The update failed, or the new version misbehaves.** The desk keeps the files it replaced. Tell your agent "go back to the previous version of the desk", or in the desk folder type `python updater.py rollback`, then start the desk. [Updates](/docs/install/updates/) explains what is kept.
- **Capitol is slow the first time.** It downloads and reads the recent House disclosures once. A minute or two, then seconds.
- **A commodity card says stale.** The scraped source changed its page. The last good value stays, dated, until the source is read again.

## Where the log is

`logs/desk-service.log` in the desk folder, or `logs/desk.log` if you started it by hand. The last thirty lines are usually enough for the agent.

## Still stuck

Four doors, and every one of them is read.

- **Tell us**, in the sidebar of the desk itself. It runs the check, shows you everything it gathered, and sends it with one press, or opens your mail app with it addressed to us. No account anywhere. The reply comes back to the same page, under Your reports, and the sidebar entry shows a mark when one is waiting. This is the door for most readers.
- [Known issues](/docs/install/known-issues/): what other readers have hit, dated, with the fix next to it. Look here first; it is often one click.
- [Discussions](https://github.com/shubhamsborkar/greeksoup/discussions): ask in the open. The answer stays up for the next reader with the same question, and search engines find it.
- [Report it](https://github.com/shubhamsborkar/greeksoup/issues/new/choose) when something is plainly broken. The template asks for what you saw and the check's printout, and that is all we need.
- Email, if you would rather not use GitHub: info@shikshannivesh.com, with the check's printout pasted in.

Whichever door, it is answered, and what we learn goes on the Known issues page the same day.
