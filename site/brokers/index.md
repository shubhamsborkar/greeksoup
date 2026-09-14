---
title: Brokers
nav: Overview
description: How GreekSoup connects to a broker account, read-only, and which six connect as the desk comes.
lead: You pick the broker on Settings, paste what it hands out from its own dashboard, and Desk · Home fills. Six connect as the desk comes. Nothing places an order.
---

## The six

<div class="cards" markdown="0">
<a href="/docs/brokers/alpaca/"><b>Alpaca</b><span>United States. Key and secret from the dashboard; a paper account has its own pair.</span><em>Holdings and cash</em></a>
<a href="/docs/brokers/icici-direct/"><b>ICICI Direct</b><span>India. App key and secret, and a login every trading day. Serves live ticks, futures and options, margin, the options tape.</span><em>The full screen</em></a>
<a href="/docs/brokers/interactive-brokers/"><b>Interactive Brokers</b><span>Worldwide. A Flex Web Service token and a query, no gateway program to run. Positions as of the previous close.</span><em>Holdings and cash</em></a>
<a href="/docs/brokers/tradier/"><b>Tradier</b><span>United States. One access token; the sandbox account has its own.</span><em>Holdings and cash</em></a>
<a href="/docs/brokers/trading-212/"><b>Trading 212</b><span>United Kingdom and Europe. A key and secret generated in the app. Invest and ISA accounts.</span><em>Holdings and cash</em></a>
<a href="/docs/brokers/zerodha/"><b>Zerodha</b><span>India. A Kite Connect app and a login every trading day.</span><em>Holdings and cash</em></a>
</div>

Any other broker with an API is [one file your agent writes](/docs/brokers/another-broker/) from that broker's documentation. A broker with no API exports a file, and Desk · Book takes it.

## What every broker shows

Holdings and cash. A line the broker does not price is marked from Yahoo's free feed, so the account is valued live whatever the broker hands out.

## What some brokers add

What the screen shows beyond that depends on what the broker gives. Live ticks on Watch · Home, open futures and options, the margin cushion, the index options tape, minute candles and a futures book on the ticker page appear when the broker's feed serves them, and a broker that serves none of them simply has a smaller Home screen. Of the six, ICICI Direct serves all of them today; the other five return holdings and cash.

## The market follows the broker

Once a broker is connected, the desk knows which market it trades in, and the home screens take that market's shape: its session hours on the status dot, its index on Risk, its currency and digit grouping, its exchanges in the add box on Watch · Home, and where the public record offers them, the results calendar, the filings block on the home ticker page and the market's own macro cards. [Markets](/docs/markets/) has the detail.

## Read-only, always

Every broker file reads. There is no order code in the desk, on purpose, and the keys you paste are the read-only kind wherever the broker offers one. If you extend the desk to trade, that is your own build, under your broker's and your regulator's rules.

## The daily login

Most brokers keep the connection alive for weeks or months once the key is set, and there is nothing to do in the morning. A broker whose regulator requires a fresh login every trading day is the exception; of the six, the two Indian ones are like that, and Settings says so next to the broker's name. On a morning you want that account live, open Settings, click *Open the broker login*, log in on the page it opens, and paste what the address bar hands back. If the redirect address in your broker app is `http://localhost:8765/settings`, it arrives on its own and there is nothing to paste. Skip the login and the desk keeps the last saved book, re-priced live, with a ribbon saying the session is off; every other screen is unaffected.
