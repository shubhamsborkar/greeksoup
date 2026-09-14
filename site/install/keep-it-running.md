---
title: Keep it running
description: How GreekSoup starts with your computer and comes back by itself if it stops, and the files that switch that on and off.
lead: Two ways to run the desk. Pick one. The one-line install already picked the second for you.
---

## Start it when you want it

Double-click **Start Desk** in the desk folder (`Start Desk.command` on a Mac, `Start Desk.bat` on Windows), then open `http://localhost:8765`. A small window stays open while the desk runs. Close the window and the desk stops. Use this if you only want the desk while you are at the screen.

## Always on

Double-click **Keep Desk Running** once (`Keep Desk Running.command` on a Mac, `.bat` on Windows). From then on the desk starts by itself when you log in, and if it ever stops, for any reason, it is back within a few seconds. Shut the laptop and it sleeps with it; open the lid and it carries on. You never start it by hand again.

The Settings screen carries the same switch, *Start with the computer*, and shows whether it is on.

**Stop Desk** switches the always-on desk off. On a Mac, double-clicking it again switches it back on; on Windows, double-click Keep Desk Running again.

## What is behind it

On a Mac it is a launch agent, a small file at `~/Library/LaunchAgents/com.research-desk.plist` that tells macOS to run the desk at login and restart it if it exits. On Windows it is a task named "Research Desk" in Task Scheduler that runs a hidden PowerShell script at logon. On Linux it is the systemd user unit `greeksoup-desk.service`. Nothing else is installed anywhere on your computer.

Two copies of the desk on one computer share the service name, so the switch on one copy stays out of the way when the other owns the service, and says so.

## How to tell it is running

The address opens. If the page is blank, [the page is blank](/docs/install/the-page-is-blank/) has the steps in order.

## What happens in daily life

You shut the computer down and switch it on again, and the desk is back once you log in. You close the laptop lid, the desk sleeps with it and carries on when you open it. Something crashes, the desk restarts itself. Nothing on the desk needs a login of its own; only a broker whose regulator requires a fresh login every trading day asks for anything in the morning, and [that is on the broker's page](/docs/brokers/).
