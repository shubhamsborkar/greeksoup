---
title: India
description: What the India market file gives the GreekSoup home screens: NSE hours, NIFTY 50, the results calendar, the integrated filings and three macro cards.
lead: The fuller of the two market files that ship. Either Indian broker, or a broker your agent writes for India, gets all of it, and so does a reader with no broker who picks India on Settings.
---

<div class="fact" markdown="0">
<b>Session</b><span>NSE regular hours, 09:15 to 15:30, Monday to Friday, in your computer's local time</span>
<b>Index</b><span>NIFTY 50</span>
<b>Currency</b><span>Rupees, grouped in lakhs and crores</span>
<b>Exchanges</b><span>NSE, then BSE; a symbol is looked up on NSE first</span>
<b>Public record</b><span>The NSE results calendar; NSE integrated filings; the ten-year yield, the repo rate and CPI; the benchmark mandis and the Rubber Board on the Commodities board</span>
</div>

## The results calendar

Under Desk · Home, for every name on the home watchlist: the next board meeting with a results purpose, from the exchange's own calendar, with days to go and the purpose as the exchange lists it. A name with no NSE listing is counted at the end of the line, not hidden. The calendar refreshes twice a day.

## The filings block on a ticker page

Open any home name and under the chart the page shows what the exchange has filed for it: the last six quarters of revenue, profit before tax, profit after tax and earnings per share with the year-over-year change where the range allows, the shareholding pattern by quarter, and the last ninety days of announcements with a link to each document. The rounding is read from each filing. Results filed before the exchange's integrated format began are not in this feed.

## The three macro cards

On Macro, in a group of their own: the ten-year yield (monthly, from FRED, with a lag of about two months), the repo rate with its full change history, and headline CPI year over year. The CPI series is the 2012-base one the statistics office still publishes, which ended in December 2025 when the base changed; the card is complete to that point and says so with its date.

## India's own prices on the Commodities board

With India as the home market, six cards on the Commodities board carry an Indian line under the global benchmark, keyless: Indore wheat (mill quality) and Indore soybean, Davangere maize, Raichur kapas (seed cotton, before ginning) and Muzaffarnagar gur (the mandi-traded sugar proxy; sugar itself sells ex-mill), each as the benchmark market's latest modal price in rupees per quintal with the day's move, from the Indian Mandi Prices API that reads agmarknet's daily arrivals; and Kottayam RSS4 from the Rubber Board's daily sheet under Natural rubber. When the named market has had no row in ten days the line is the state's daily average and says so. Click the card for the line against the global price and the state average's move on the week. An Indian broker that serves MCX adds its front-month futures on top. Rice is not there on purpose: mandi rows mix basmati and common grades under one name.

## The economic calendar

Indian prints appear beside the US ones for the next ten days when a feed key is set.

## Codes and symbols

On Watch · Home and the ticker page a name is its NSE symbol (RELIANCE, TCS), or the broker's own code where the broker has one and the desk translates. Behind the scenes the desk pairs it with Yahoo's symbol (`RELIANCE.NS`, or `.BO` for a BSE-only listing) for anything the broker does not price.
