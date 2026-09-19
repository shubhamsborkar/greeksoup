---
title: The words on the screens
nav: Glossary
description: What the terms on the GreekSoup screens mean, as the desk uses them: 13F, 13D and 13G, Form 4, cluster buy, put wall and call wall, expected move, skew, open interest, days to cover, short-volume ratio, 2s10s, breakeven, OAS, beta, drawdown, tracks index, DCF, PTR.
lead: Every term as the desk uses it, one paragraph each, with the screen it lives on. Where a number is computed, the arithmetic is here.
---

## Ownership and filings

**13F** (Funds). The quarterly holdings report a US investment manager with more than a hundred million dollars files with the SEC, due forty-five days after the quarter ends. It lists US long positions only: no shorts, no cash, no non-US listings, and it is a snapshot as of the quarter's last day.

**13D and 13G** (Funds). The forms filed within days of crossing five percent of a company's shares: 13D when the holder may seek to influence the company, 13G when it holds passively.

**Form 4** (Desk · Home, the ticker page). The SEC form an officer, director or ten-percent holder files within two business days of buying or selling the company's stock. **Cluster buy**: several insiders buying in the same short window, which the desk marks on the insider tape.

**PTR** (Capitol). A periodic transaction report, the form a member of Congress files within forty-five days of a trade over a thousand dollars, with the amount as a band rather than a figure. The **lag** column is the days between the trade and the disclosure.

**CIK** (Funds). The SEC's number for a filer, which is how a fund is added to your list.

## The options tape (Flow)

**Open interest** is the number of contracts standing at a strike. **Put/call on open interest** is total put open interest over total call open interest; **put/call on volume** the same on today's traded contracts.

**Put wall** and **call wall**: the strike below spot with the most put open interest, and the strike above spot with the most call open interest, within the ninety-day window.

**Expected move**: the move the options market has priced to the nearest expiry, from the at-the-money straddle, shown as a percent of spot with the expiry date.

**IV30**: implied volatility thirty days out, annualised. **Skew**: the implied volatility of a put against a call at the same distance from spot; positive when puts are dearer.

**Unusual strikes**: today's volume at least twice the standing open interest, with real premium; positions that did not exist yesterday. **OI build**: open interest against the previous day's snapshot on disk.

## Short interest (Short)

**Short interest**: open short positions at the settlement date, from FINRA's consolidated report, twice a month, published about nine days after settlement.

**Days to cover**: short interest divided by average daily volume; how many days of normal trading it would take to buy the short position back.

**Short-volume ratio**: the share of one day's off-exchange volume that was marked short, from FINRA's daily file. Forty to fifty percent is normal market-making; the signal is a change against a name's own twenty-day average. It is flow, not open positions, and the desk keeps it on its own side of the screen.

## Macro (Macro)

**2s10s**: the ten-year Treasury yield minus the two-year, in percentage points; negative means the curve is inverted.

**10Y breakeven**: the ten-year Treasury yield minus the ten-year inflation-protected yield; the inflation the bond market has priced. **5y5y forward**: the same, for the five years starting five years from now. **10Y real yield**: the inflation-protected ten-year itself.

**OAS**: option-adjusted spread, the extra yield a corporate bond index pays over Treasuries, high yield and investment grade on separate cards.

**Delta** on a card: the change over about a month. The sparkline is two years.

## Risk (Risk)

**Beta**: how much the book moves for a one percent move in its index, from the last year of daily closes; 0.5 means a one percent index day is half a percent here.

**Volatility**: the annualised standard deviation of daily returns; a normal day is about that figure divided by sixteen.

**Max drawdown**: the worst fall from a peak in the past year.

**Tracks index**: the correlation of the book's daily returns with the index's; the square of it is the share of daily movement the index explains.

**The five percent line**: beta times five percent times the account, what a five percent index day costs by that estimate.

**Leverage**: positions at full underlying value over the account; futures count at underlying value, so a leveraged book shows more than the account.

## The ticker page

**DCF sandbox**: a discounted cash flow, seeded from the provider's statements, every input yours to change; it needs a data provider key.

**Street view**: the average analyst target and the count of strong buy, buy, hold, sell and strong sell, from the free feed or the provider.

**Receipt** (Chain): how firm a link on a value chain is: disclosed in a filing, on record, or reported.
