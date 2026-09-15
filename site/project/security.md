---
title: Security
nav: Security
description: The GreekSoup threat model in plain words, what the desk does about each threat, the honest limits, whether to run it on your own computer or a server, and how to report a problem privately.
lead: The desk holds your book, your keys and your research. Here is what can go wrong, what the desk does about each thing, and what it cannot do for you. Read this once before you connect a broker.
---

## The shape of it, in six lines

- The desk listens at an address only your own computer can reach, on both of its own names (`localhost` and `127.0.0.1`), and on nothing else. Another machine on your network cannot open it.
- It has no login of its own, because nothing outside your computer can reach it. Two guards carry that weight, described below.
- Your keys live in one settings file inside the desk folder. The update never touches it, the backup never includes it, and the page your AI reads tells the AI not to read it.
- There is no order path, on any broker. Every broker file uses that broker's read endpoints and nothing else.
- Nothing about you leaves your computer unless you connect something that needs it: your broker, a data provider, your AI. [What it talks to](/docs/install/what-it-talks-to/) is the whole list.
- No telemetry, no analytics, no account, no crash reports. The once-a-day version check carries no identifier.

## What can go wrong, and what the desk does about it

**A web page you visit reaches the desk.** A page on any site can try to send a request to `localhost`. Two guards refuse it. The desk checks the browser's `Origin` header on every request and answers only its own pages; a request that names another site, or a page with no site at all, gets a refusal before it is read. And it checks the `Host` header on every request, so a page that has tricked your browser into calling `localhost` by another name (DNS rebinding) is refused too. A program running on your own computer, your AI agent or a command line, sends no `Origin` and is let through, because it is you.

**Someone with access to your computer reads your book.** They can. The desk trusts your computer the way your documents folder does. If several people share a computer, they share the desk; run it under your own user account and lock the screen.

**The AI you chose sees your holdings.** It does, when you ask. The Ask box sends your question together with the numbers on the screen you are on, and on Desk · Home those numbers are your book. That is the point of asking, and it is also a fact to know. Where it goes is the one address you chose under Your AI: a lab's key, an app you already pay for on this computer, or a model running on this computer through Ollama or LM Studio, which never leaves it. Nothing is sent until you press Enter.

**An app on this computer answers the Ask box.** With Claude Code, Codex or Gemini CLI chosen under Your AI, the desk runs that app with the question on standard input and reads what comes back on standard output. The desk never sees the app's login; the app reaches its own provider under your own account, exactly as it would from a terminal. The brief tells the app to answer from the data and to run no commands and edit no files; the app's own permission settings still apply, and you should read them once.

**A plugin does something you did not expect.** A plugin is a folder you bring in yourself, from the list we publish, from a folder or from a zip. Its screen runs inside the desk and can read every address the desk answers, and a door can run one command on your computer, the one it names. The desk shows what a plugin adds and what it talks to before it goes in, and removes it in one click. Treat a plugin you did not write the way you would treat any program you install: read it first, or ask your agent to read it and tell you what it does. Nothing is brought in on its own.

**A feed lies.** Every number comes from a source that can be wrong, late or restated, and the desk names the source on the screen. Verify against the primary source before acting on anything. The desk never acts on your behalf, so a wrong number costs you a wrong read, not a trade.

**An update breaks something.** The desk keeps the files each update replaced, for the last three versions, and one line brings any of them back. Every file you own carries a format number; when a version changes a file's shape the desk keeps a copy first and says so on the banner. [Updates](/docs/install/updates/).

## The honest limits

- **No login means the computer is the boundary.** Anyone who can sit at your unlocked computer, or run a program on it, can read the desk. That is the same boundary as your files.
- **A plugin is trusted code.** It runs with the desk's own reach. Read what you install.
- **The AI is outside the boundary by your choice.** A lab's key or an app you pay for sends what you ask about to that lab. A local model does not.
- **The desk is not built to be reached from elsewhere.** It does not carry the login, the encryption or the audit log that a service open to the internet needs.

## Your own computer, or a server?

Your own computer. The desk was built to sit beside you, read your broker under your eyes and keep your research in a folder you can open in Finder or Explorer. Its whole safety story is that nothing else can reach it, and that story holds on a laptop.

A rented server (a VPS) turns that around. Its front door faces the internet; to read the desk from your laptop you would open a port, and then the desk's lack of a login becomes the problem rather than the answer. If you must run it there, put it behind a reverse proxy with encryption and a login of your own, keep the desk itself bound to the server's own address as it ships, and understand that we do not document or test that path. [Your computer or a server](/docs/install/your-computer-or-a-server/) says more.

The reason some readers of other agent projects moved to a server, that the agent had the run of their files and could be turned against them by a page it read, does not apply in the same way here. The desk runs no agent of its own, executes nothing a page or a feed says, and takes instructions only from you. The one program it can run is the app you chose under Your AI, with a brief that tells it to read and answer only.

## Keeping your copy safe

- Do not expose the port to the internet, and do not put it behind a tunnel you do not understand.
- Use read-only broker keys where the broker offers them, and a paper account while you learn the desk.
- Read a plugin before you install it, or have your agent read it.
- Back up from Settings before a big change. The backup carries your data and your research vault, never your keys.
- Keep the desk on the current version; the banner tells you when one exists.

## If you want to check

In the desk folder, `python doctor.py` prints every setting by name and never by value, and which sources it can reach from your computer. Nothing in the printout is private; give it to your agent or paste it into a report.

## Reporting a problem

Open a GitHub issue titled `Security` with no details in it, and we will reply with a private channel within a few days. Please do not post the details publicly first. The repository's `SECURITY.md` says the same.
