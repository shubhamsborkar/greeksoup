---
title: Your computer or a server
nav: Your computer or a server
description: Whether to run GreekSoup on the computer in front of you or on a rented server, and why the desk's safety story holds on a laptop and turns around on a VPS.
lead: Readers of other local agent projects learned to fear the laptop and rent a server. The desk is a different kind of program, and the answer here is the other way round.
---

## The short answer

Run it on the computer you research on. The desk was built for that: it listens only to that computer, it keeps your keys and your research in folders you can open, and it takes instructions from nobody but you. Everything on the [Security](/docs/project/security/) page rests on nothing else being able to reach it, and that is true of a laptop as it ships.

## Why the fear existed elsewhere

The agent projects people worried about run an assistant with the run of your files, your mail and your logins, and read pages and messages from the outside world that can carry instructions the assistant then follows. On a personal computer that puts your real files in the blast radius, so people moved the agent to a throwaway server where a compromise costs less. That was a sound instinct for that kind of program.

The desk is not that kind of program. It runs no agent of its own. It reads feeds and filings and draws them; it never executes what a page or a feed says. The one program it can run is the AI app you chose under Your AI, with a brief that says read and answer, and with that app's own permission settings still in force. Your research vault is plain files the desk writes only when you press Save. The blast radius of a bad page is a wrong number on a screen, which the source line beside it lets you check.

## What a server would change

A rented server has a front door on the internet. The desk still binds to that server's own address, so by itself it is unreachable from outside, and to read it from your laptop you would open a way in. At that moment the desk's lack of a login, which is its answer on a laptop, becomes a hole on a server. A reverse proxy with encryption and a login of your own closes it, and a firewall that allows your own address only closes it further, but you now own a small piece of infrastructure and its upkeep. We do not document or test that path, and a broker key on a machine you do not sit at deserves a moment's thought.

## The cases where a second machine makes sense

- **A desk that must be up all day** for the results calendar, the tape and the alerts, while your laptop sleeps. A small always-on computer at home, a Mac mini or a mini PC on your own network, gives you that without a public front door. Install the desk there and open it from that machine, or from your laptop over your own network with a tunnel you understand.
- **Two computers, one vault.** Point both desks at a folder a drive you already use syncs (iCloud Drive, Google Drive, Dropbox, OneDrive), from Settings under Where the vault lives. The research follows you; the keys stay on each machine. [Two computers](/docs/setup/two-computers/).

## What to do either way

- Keep the desk bound to its own computer, as it ships.
- Prefer read-only broker keys and a paper account while you learn it.
- Read a plugin before it goes in.
- Keep the desk current; the banner tells you when a newer version exists.
