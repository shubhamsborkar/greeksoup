---
title: Alpaca
description: Connect an Alpaca account to GreekSoup: where the keys come from, the paper switch, and what the desk shows.
lead: United States. A key ID and a secret from Alpaca's dashboard; a paper account works the same way with its own pair.
---

<div class="fact" markdown="0">
<b>Market</b><span>United States; the home screens take the US shape</span>
<b>You paste</b><span>API key ID, API secret; the Paper switch on for a paper account</span>
<b>Daily login</b><span>None; the keys stay valid until you revoke them</span>
<b>The desk shows</b><span>Holdings and cash, with buying power; every line priced live by the desk</span>
</div>

## Where the keys come from

In Alpaca's dashboard, under **API keys**, generate a key. Alpaca shows a key ID and a secret once; copy both. A paper-trading account has its own dashboard and its own pair, and the desk needs to know which kind it is, so switch **Paper account** on for a paper pair.

## On Settings

Pick **Alpaca · United States** under Your broker, paste the key ID and the secret, set Paper if it applies, and click **Save and connect**. The desk asks Alpaca for the account and the positions at once and says how many holdings it found. A wrong pair, or Paper set the wrong way, comes back as "Alpaca did not accept these keys" with the reason.

## What Desk · Home shows

Every position with quantity, average cost, the live mark, value, profit since cost and the day's move; cash and buying power. Alpaca hands out a current price for each position, and where it does not the desk marks the line from Yahoo. Watch · Home quotes through Yahoo, the US way, and the status dot follows US hours.

## What it does not show

No futures, no options tape, no margin bar: Alpaca's read for individuals does not serve them, so those panels stay out of the way. The options tape on US names is on the Flow screen for every reader, from CBOE.

## Read-only

The desk reads the account and the positions and nothing else. Alpaca keys can trade, so treat the pair like a password: it sits in the settings file on your computer and the desk never shows it back.
