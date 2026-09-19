---
title: A number looks wrong
nav: A number looks wrong
description: What to do when a number on a GreekSoup screen looks wrong: read the source the screen names, know which feeds are delayed or restated, check one figure against the primary record, and report a misread with the screen and the symbol.
lead: Every number on every screen names its source, and every source can be wrong, late or restated. This page is the order to check in, and the line between a feed's fault and the desk's.
---

## Read the source the screen names

Under or beside the number: Yahoo, your broker, SEC EDGAR, CBOE, FINRA, FRED, Nasdaq, Frankfurter, Trading Economics, the exchange, the provider. The date or time it was read is on the screen too. [Data sources](/docs/setup/data-sources/) says what each one gives and how fresh it is.

## The usual reasons

- **Delayed.** Yahoo's quotes are near live for US listings and fifteen to twenty minutes behind on most other exchanges; CBOE's chains are fifteen minutes delayed; FINRA's short interest settles twice a month and publishes about nine days later; a 13F is a quarter-end snapshot filed up to forty-five days after.
- **Restated.** A filing amends an earlier one; the desk shows the latest it read, and the earlier figure you remember was the earlier filing.
- **The feed is resting.** An amber line says the page is the last read with its time. [The feed is resting](/docs/help/the-feed-is-resting/).
- **A currency.** Desk · Book adds up per currency and never across; a total that looks small is one currency's.
- **A results date is an estimate.** Until the company announces, the Calendar shows an estimate and says so.
- **Futures at underlying value.** Risk counts a future at the full value of what it controls, so a leveraged book shows positions worth more than the account.

## Check one number against the primary record

The filing on EDGAR, the exchange's page for the listing, the central bank's series on FRED, the broker's own statement. One number, and if it matches, the rest of the screen is drawing from the same place. If it does not match, note the screen, the symbol, the number shown and the number in the record.

## Tell us

If the desk misread something, the source is right and the screen is wrong, that is ours to fix. Tell us in the sidebar sends the report with the screen and the symbol, or [file an issue](https://github.com/shubhamsborkar/greeksoup/issues/new/choose). If the source is wrong, the desk cannot make it right; it can only name it, which it does.
