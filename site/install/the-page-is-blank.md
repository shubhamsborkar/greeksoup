---
title: The page is blank
description: What to do when the GreekSoup address does not open, in order.
lead: Four things, in order. Most blank pages are the first one.
---

## In order

<ol class="steps" markdown="1">
<li markdown="1">
**Open the address in a fresh tab.** Close the tab that shows nothing and open `http://localhost:8765` in a new one. A tab that once found the desk down keeps showing it down even after it is back, and a reload does not clear that.
</li>
<li markdown="1">
**Wait thirty seconds and open it again.** If the always-on service is on, it restarts the desk on its own within a few seconds of a stop.
</li>
<li markdown="1">
**Double-click Start Desk** in the desk folder. A window opens and prints what the desk is doing. If it prints an error, that is the thing to fix, and the next step is where to take it.
</li>
<li markdown="1">
**Give it to your agent.** Open the desk folder in your AI agent, tell it to read `README.md`, and paste what the window said, or the tail of `logs/desk-service.log` from the desk folder. Describe the problem in your own words. If you have no agent, the same text is what to search for.
</li>
</ol>

## Other things a page can say

- **"retry in a few minutes"** on a fresh install: Yahoo's free quotes rate-limit bursts. The desk backs off and retries on its own.
- **A slow first visit to Capitol**: it downloads and reads recent House disclosures once. A minute or two, then seconds.
- **"The desk is already running"** in the window: another copy is on the same door number. Open the address; it is that copy.
- **A broker screen says the session is off**: that is the broker's daily login, not a fault, and [the broker's page](/docs/brokers/) says what to do.
