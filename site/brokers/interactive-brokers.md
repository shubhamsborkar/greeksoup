---
title: Interactive Brokers
description: Connect an Interactive Brokers account to GreekSoup through the Flex Web Service, with no gateway program to run.
lead: Worldwide. A token and a query from Client Portal, and nothing to keep running on your computer. Positions come as of the previous close and the desk prices them live.
---

<div class="fact" markdown="0">
<b>Market</b><span>Follows the US shape; Interactive Brokers accounts hold shares from many exchanges and each line carries its own Yahoo symbol</span>
<b>You paste</b><span>The Flex Web Service token and the Query ID</span>
<b>Daily login</b><span>None; the token lasts as long as you set it to in Client Portal</span>
<b>The desk shows</b><span>Holdings and cash, as of the previous close, priced live by the desk</span>
</div>

## Where the keys come from

In Client Portal open **Performance & Reports**, then **Flex Queries**.

1. Create an **Activity Flex Query**. Include the **Open Positions** section; add the **Cash Report** section as well if you want the cash line. Save it and note its **Query ID**, the number next to its name.
2. On the same page switch on the **Flex Web Service** and copy the **token** it shows. Set its expiry as long as you like; the desk asks again when it runs out.

No Trader Workstation, no gateway, nothing has to be open on your computer. The desk asks Interactive Brokers for the report, waits a few seconds, and reads it.

## On Settings

Pick **Interactive Brokers · worldwide**, paste the token and the Query ID, and click **Save and connect**. A wrong token or query comes back as "Interactive Brokers said: ..." with the reason from their side, and "did not finish the report in time" means try again in a minute.

## What Desk · Home shows

Every open position with quantity and average cost. The report is the previous close, so the desk marks every line from Yahoo through the share's own symbol, whichever exchange it trades on, and values the account live from that. Cash from the Cash Report section, if you included it.

## What it does not show

No futures, no margin bar, no options tape through this read; those panels stay out of the way. If the query includes other sections they are ignored.
