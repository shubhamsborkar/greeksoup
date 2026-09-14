---
title: ICICI Direct
description: Connect an ICICI Direct account to GreekSoup through the Breeze API: the app, the daily login, and the full Home screen it serves.
lead: India. An app key and secret from api.icicidirect.com, free for its clients, and a login every trading day. This is the broker whose feed serves everything the Home screen can show.
---

<div class="fact" markdown="0">
<b>Market</b><span>India; the home screens take the Indian shape (NSE hours, NIFTY 50, rupees)</span>
<b>You paste</b><span>App key, app secret; then the day's login each trading morning</span>
<b>Daily login</b><span>Yes; the session ends at midnight, as the regulator requires</span>
<b>The desk shows</b><span>Holdings, cash, open futures and options, margin used, the index options tape, live ticks, minute candles, a futures book</span>
</div>

## Where the keys come from

At api.icicidirect.com register an app once. Set its redirect address to this desk's Settings address, `http://localhost:8765/settings`, so the daily login can land in the page by itself. Copy the app key and the app secret.

## On Settings

Pick **ICICI Direct (Breeze) · India**, paste the key and the secret, and click **Save and connect**. The desk saves them and then asks for today's login, because this broker needs one before anything can be read.

## Every trading morning

Click **Open the broker login**. Log in on the page that opens. When it finishes, the page jumps to a localhost address with `apisession=` in it; if your app's redirect address is the desk's Settings address, that value arrives in the page on its own and the desk connects. Otherwise copy the value after `apisession=` (or the whole address) into the box and click **Connect**. Desk · Home is live a moment later.

Skip the login and the desk keeps showing the last saved book, re-priced live through Yahoo, with a ribbon saying the session is off. Cash, margin and the futures marks stay as the broker last reported them, because those are the account's own numbers. Every other screen is unaffected.

## What Desk · Home shows

Everything the screen can show, because the desk was first built against this feed:

- Holdings with the broker's own marks, the ones it values the account and any margin against.
- Open futures and options, with expiry, days to expiry, notional and mark-to-market, and a three-day sparkline under each underlying.
- Margin used as a bar, with the free limit and the implied collateral.
- The index options tape: put/call, the fresh open-interest lean, the expected move, support and resistance, and the five percent put/call skew, for the indices in `data/fno_watchlist.json`.
- Live ticks on Watch · Home in market hours, with the order book columns, and the broker's own symbol master behind the search box.
- On a ticker page: one-minute and five-minute candles, the futures book with bid, ask and open interest, and the 52-week and lifetime range.
- On Commodities: MCX front-month futures on the matching cards and the Rubber Board's daily sheet on rubber.

## Codes

This broker uses its own short codes for shares (RELIND for Reliance Industries, say), and the desk's search box understands them, the exchange symbol and the company name alike. Holdings open on the ticker page by that code, and the page shows the exchange symbol beside it.

## More than one account

This file supports several accounts at the same broker. Add a line to `ACCOUNTS` in `breeze_session.py` and the matching key pair in the settings file, and your agent can do both from a sentence. Only the first account's session is required each morning; the others fall back to their last saved book, re-priced live.
