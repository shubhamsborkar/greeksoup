---
title: Tradier
description: Connect a Tradier account to GreekSoup with one access token.
lead: United States. One access token from Tradier's dashboard; the sandbox account has its own.
---

<div class="fact" markdown="0">
<b>Market</b><span>United States</span>
<b>You paste</b><span>The access token; an account number if the profile has several; the Sandbox switch on for the paper account</span>
<b>Daily login</b><span>None</span>
<b>The desk shows</b><span>Holdings and cash; every line priced live by the desk</span>
</div>

## Where the keys come from

In Tradier's dashboard, under **API access**, copy the access token. The sandbox, Tradier's paper account, has a token of its own, and the desk needs to know which it is, so switch **Sandbox account** on for that one.

If your profile has more than one account, put the account number you want in the box; leave it empty and the desk reads the first account on the profile.

## On Settings

Pick **Tradier · United States**, paste the token, set Sandbox if it applies, and click **Save and connect**. A wrong token, or Sandbox set the wrong way, comes back as "Tradier did not accept this token" with the reason.

## What Desk · Home shows

Every position with quantity and cost basis. Tradier's positions read carries no price, so the desk marks every line from Yahoo and values the account live from that. Cash from the balances read.

## What it does not show

No futures, no margin bar, no options tape through this read. The options tape on US names is on the Flow screen for every reader.
