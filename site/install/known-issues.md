---
title: Known issues
nav: Known issues
description: Every problem a GreekSoup reader has reported, dated, with what it means and the version that fixed it. Newest first.
lead: If what you are seeing is on this list, the fix is written next to it. If it is not, tell us and it will be, the same day.
---

Each line says what a reader saw, what it meant, and where it stands. Fixed means the version named carries the fix; click **Update the desk** in the strip, or paste the install line again if the desk is not running.

## Windows

- **19 September 2026. Bitdefender says `install.ps1` is infected and the update stops with "Permission denied".** A false alarm on the desk's own install script, which downloads a file and runs it the way every installer does; the update unpacked it and the antivirus locked it. Fixed in 2026-09-19.103 and .104: the install script no longer travels inside updates, every installed copy removes it from its own folder, and an update that cannot read a file stops before it writes one. What to do: let the antivirus restart the PC if it asks, then click Update once more. [The whole of it.](/docs/install/windows/#if-your-antivirus-speaks-up)
- **15 September 2026. The install line ends with "ERROR: Access is denied" and the desk does not start.** Windows refused to make the start-at-logon task, which happens on PCs without administrator rights. Fixed in 2026-09-15.6: the task is made for the user only, and when Windows still refuses, a shortcut in the user's own Startup folder takes its place. What to do: paste the install line again.
- **The browser says nothing is at `localhost:8765` while the desk is running.** On some Windows PCs that name points at one address first and the desk listens on the other, so the name says nothing is there while the desk runs perfectly well. The installer now checks the desk at `127.0.0.1`. What to do: open `http://127.0.0.1:8765`.
- **PowerShell refuses to run the install line ("running scripts is disabled").** A policy on the PC, not a fault. The [with an agent](/docs/install/with-an-agent/) path needs no script.

## Mac

- **A `.command` file "cannot be opened because it is from an unidentified developer".** Apple's gate on any file downloaded from the internet, once. Right-click the file, choose Open, then Open again. The one-line install in Terminal is not gated.

## Every system

- **"retry in a few minutes" on a fresh install.** The free quote feed limits bursts from a new address. It clears by itself; nothing to do.
- **A broker screen says the session is off.** The broker's daily login, not a fault. The Settings screen has the box for today's token; [the broker's page](/docs/brokers/) says where it comes from.
- **The update was interrupted (the network dropped, the PC shut down).** Since 2026-09-19.104 nothing is written until every file can be read, the version is stamped last, and the files replaced are kept for three versions. What to do: click Update again.

## Not on the list?

[Ask in Discussions](https://github.com/shubhamsborkar/greeksoup/discussions), where the answer helps the next reader too, [report it](https://github.com/shubhamsborkar/greeksoup/issues/new/choose) with the printout of `python doctor.py`, or email info@shikshannivesh.com. Whichever way, it lands here.
