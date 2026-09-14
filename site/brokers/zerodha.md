---
title: Zerodha
description: Connect a Zerodha account to GreekSoup through Kite Connect, with a login every trading day.
lead: India. A Kite Connect app, which Zerodha charges for, and a login every trading day. The Indian market file serves the home screens.
---

<div class="fact" markdown="0">
<b>Market</b><span>India; the home screens take the Indian shape (NSE hours, NIFTY 50, rupees, the NSE results calendar and filings)</span>
<b>You paste</b><span>API key, API secret; then the day's login each trading morning</span>
<b>Daily login</b><span>Yes; the session ends at six in the morning the next day</span>
<b>The desk shows</b><span>Holdings and cash, priced live by the desk</span>
</div>

## Where the keys come from

At developers.kite.trade create a Kite Connect app. Zerodha charges a monthly fee for it. Set the app's redirect address to this desk's Settings address, `http://localhost:8765/settings`, so the daily login can land in the page by itself. Copy the API key and the API secret.

## On Settings

Pick **Zerodha (Kite Connect) · India**, paste the key and the secret, and click **Save and connect**. The desk saves them and then asks for today's login.

## Every trading morning

Click **Open the broker login**. Log in on Zerodha's page. When it finishes, the page jumps to your redirect address with `request_token=` in it; if that is the desk's Settings address, the desk exchanges it for the day's session on its own and connects. Otherwise copy the value after `request_token=` (or the whole address) into the box and click **Connect**.

Skip the login and the desk keeps showing the last saved book, re-priced live through Yahoo, with a ribbon saying the session is off. Every other screen is unaffected.

## What Desk · Home shows

Every holding with quantity and average cost, marked live from Yahoo through its NSE or BSE symbol, and cash from the margins read. Watch · Home takes NSE and BSE symbols and quotes them through Yahoo, fifteen to twenty minutes behind in the session. The home ticker page shows the exchange's filings: quarterly results, shareholding and the last ninety days of announcements. The results calendar for the home watchlist sits under Desk · Home, and Macro carries the ten-year, the repo rate and CPI.

## What it does not show

No live ticks, no futures and options, no margin bar, no options tape: this file reads holdings and cash. Those are optional additions a broker file can grow, and [another broker](/docs/brokers/another-broker/) describes the shape; an agent can add them from Zerodha's documentation.
