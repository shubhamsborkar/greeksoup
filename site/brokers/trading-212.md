---
title: Trading 212
description: Connect a Trading 212 Invest or ISA account to GreekSoup with a key generated in the app.
lead: United Kingdom and Europe. A key and a secret generated in the app. Invest and ISA accounts; the practice account has its own pair.
---

<div class="fact" markdown="0">
<b>Market</b><span>Follows the US shape; each line carries its own Yahoo symbol, London listings included</span>
<b>You paste</b><span>API key, API secret; the Practice switch on for the practice account</span>
<b>Daily login</b><span>None</span>
<b>The desk shows</b><span>Holdings and cash; every line priced live by the desk</span>
</div>

## Where the keys come from

In the Trading 212 app: menu, **Settings**, **API**, **Generate API key**. Give it the account-data and portfolio permissions, and nothing more; the desk only reads. You get a key and a secret. Invest and ISA accounts only, which is what Trading 212's read allows.

The practice (demo) account has its own pair, so switch **Practice account** on for that one.

## On Settings

Pick **Trading 212 · United Kingdom, Europe**, paste the key and the secret, set Practice if it applies, and click **Save and connect**. A wrong pair comes back as "Trading 212 did not accept the key and secret". If Trading 212 asks the desk to slow down, it says so and retries on the next refresh.

## What Desk · Home shows

Every position with quantity and average cost, cash from the account's cash read, and every line marked live from Yahoo through the share's own symbol (a London listing opens as its `.L` symbol). Trading 212's read is marked beta by Trading 212 and its position shape has changed once already; the desk reads both shapes.

## What it does not show

No futures, no margin bar, no options tape through this read.
