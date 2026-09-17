---
title: Releases
nav: Releases
description: What changed in GreekSoup, newest first, read from the same VERSION file your desk reads when it checks for an update.
lead: Newest first. The current version is 2026-09-16.98. Your desk reads this same list once a day and offers the update with one click.
---

## 2026-09-16.98

*16 September 2026, release 98.* A home name added by company name (HDFCBANK.NS) reads its exchange record again: quarterly results, corporate filings and shareholding are asked for HDFCBANK on the NSE, which the exchange knows, instead of HDFCBANK.NS, which it does not; the blocks said the exchange was not answering. A name from another market's exchange opened from Watch · Home (SAP.DE, 7203.T) now gets the free feed's page, with valuation, financials and estimates, instead of the home market's blocks asking an Indian exchange about a German company.

## 2026-09-16.97

*16 September 2026, release 97.* A restart keeps the Commodities and Chain records on disk. Each boot reconnected the same broker and, treating that as a change of broker, threw both records away, so every newer version rebuilt them from nothing and spent the free feed's daily allowance doing it; that is where a run of too many requests came from. Changing the broker on Settings still starts them afresh.

## 2026-09-16.96

*16 September 2026, release 96.* A contract, an index or a currency pair on the ticker page (CL=F, ^NSEI, EURUSD=X) is never handed to the company search when the feed is resting: Open the full chart on WTI crude came back as Cleveland-Cliffs, the company whose letters it shares. The board's own copy of the record now comes first for a contract.

## 2026-09-16.95

*16 September 2026, release 95.* A broker code on the ticker page (PNGADG, the code ICICI Direct gives P N Gadgil) is priced by the free feed through its exchange symbol (PNGJL.NS) whenever the broker's quote feed has nothing for it; the page said no quote and stopped. On Settings, the link beside the version now checks and brings a newer version in with the one click; the strip on every screen keeps doing the same. Open the full chart on a commodity card opens from the board's own copy of the record when the free feed is resting, instead of a page that says too many requests.

## 2026-09-16.94

*16 September 2026, release 94.* A name on Watch · Home that was added by company name from another exchange (SHEL.L, ASML.AS, 7203.T) opens its ticker page again on a desk with a home broker connected: the broker was asked for it, knew nothing, and the page said no quote; the free feed that prices it on the list now prices the page too.

## 2026-09-16.93

*16 September 2026, release 93.* The desk looks for a newer version every four hours instead of once a day, so the strip that offers it appears the same day a version ships; on Settings the version line carries "check for a newer version" for a reader who wants to ask now. A desk whose home market is the US no longer shows Watch · Home beside Watch · US (the same names with fewer columns); Settings shows it again in one click. Bringing a version in still takes the reader's click on the strip unless Newer versions is switched on in Settings.

## 2026-09-16.92

*16 September 2026, release 92.* A commodity with an exchange contract opens on the ticker page. The detail panel on Commodities carries Open the full chart for every card priced from a contract (crude, gold, copper, wheat and the rest): the desk's own chart with every bar size, chart type, the indicators, drawings kept as a plain file, the drawdown view and Save chart to notes; a benchmark with a monthly series keeps its line on the board. A name opened from Global (SAP.DE, 7203.T) reads through the free feed's own path again; it was sent down the home market's path and came back with no quote. On the ticker page a contract asks TradingView for its continuous symbol (NYMEX:CL1!); where their embed does not carry it, the desk's chart stands in and the page says so.

## 2026-09-16.91

*16 September 2026, release 91.* The landing page's questions read against the desk of today: where the keys and the daily session live, picking the AI app question by question, what the Ask box carries from a ticker page, which screens take a name at the top, Build mode from inside the desk; and two new ones, TradingView's chart at a click and which brokers ask for a daily login.

## 2026-09-16.90

*16 September 2026, release 90.* The landing page catches up with the desk. greeksoup.ai now says sixteen screens (Calendar joined at .74), fifteen of them with no key; the rows for Desk · Home, Any ticker, Flow, Short, Calendar, Chain, Macro and Settings say what those screens do today; a fourth figure draws the drawdown view from the desk's own daily record; every screenshot is re-taken from this version; Nasdaq joins the public record on the page and in the desk's own security page; the Your AI block says every AI app on the computer is a door, picked question by question, and that Build mode changes the desk. On a desk whose home market is the US, the empty hand-kept tiles under The US desk step aside the same way they do elsewhere.

## 2026-09-16.89

*16 September 2026, release 89.* TradingView's chart sits inside its box. Their embed script puts its frame in place of the child that carries their widget class; the desk's child had no such class, so the frame was added below the box and clipped, which showed as a blank chart with their toolbar at the foot, and a click inside it (an interval change) scrolled the panel's own header out of sight. The child carries their class now and the frame fills the box, header and switch in place.

## 2026-09-16.88

*16 September 2026, release 88.* The US market pulse without a key. Biggest gainers, biggest losers, the most active by dollars traded and the sector snapshot now come from the free public record (every large and mega cap with today's move, volume and sector, in one read), so the panel on Desk · Home fills for every reader; a data key still brings the whole market, small caps included.

## 2026-09-16.87

*16 September 2026, release 87.* The economic calendar reads today's prints from the calendar page when the free feed's calendar endpoint refuses the address while quotes and charts still answer; the card says it is today only and looks for the full sixty days again in ten minutes.

## 2026-09-16.86

*16 September 2026, release 86.* A watchlist built on the free feed no longer kills the broker session. Watch · Home names added as Yahoo symbols (before a broker was connected, or by choice) went unpriced once a broker was on, and a pass over them with no broker answer marked the session dead, which emptied the options tape and could darken Desk · Home. Free-feed names now stay priced from the free feed beside the broker's own names, and only a silent pass over the broker's names says anything about its session. An empty options tape is retried within a minute.

## 2026-09-16.85

*16 September 2026, release 85.* A screen rebuild that fails writes one line to the desk log with the reason, instead of keeping the old copy in silence; Settings' state names the home broker, the connected clients and what is building right now.

## 2026-09-16.84

*16 September 2026, release 84.* The options tape reads the home broker's own session. A hook in the home broker's file was handed whichever client was connected when the home broker was not (Alpaca's, while ICICI waited for its login), so the tape read nothing and the empty answer was kept for ten minutes. The home client is now the home broker's only; an empty or failed tape is retried within two minutes, and a failed read says why on the card.

## 2026-09-16.83

*16 September 2026, release 83.* A broker error has a way out, and two brokers share a market. Every broker error on Settings (keys, Check, today's login) carries an Ask your AI about this button that puts the broker, its file, the contract and the exact words into the Ask box in Build mode, for the reader's own AI to work out. Two brokers in one market now sit side by side on that market's desk, each its own block, the desk's strip adding them (the same broker twice, with keys per account, is still to come). The futures and options table scrolls sideways where it is wider than the page. After a broker connects, the screens that read it are rebuilt at once rather than served from the pre-connect copy for their TTL (the options tape sat empty for ten minutes after a login). Settings' list of brokers readers ask about is rewritten from a check of each broker's own developer page today: Groww, Dhan, Upstox, Angel One, Fyers, 5paisa, Kotak Neo, HDFC Securities, Schwab, tastytrade, Public, Webull, moomoo, E*TRADE, Saxo, and the ones with no API. Two alert texts lose their dashes.

## 2026-09-16.82

*16 September 2026, release 82.* ICICI Direct connects from the keys and the session key the reader pasted. The broker's file read an older session file instead of the one Settings writes, so a fresh login was refused as stale; it now builds the session from the saved keys and the day's apisession value, and the broker's own words come through when the keys are wrong. The desk also trusts a certificate bundle for every https call, so a Python installed without one (the python.org build on a Mac) no longer fails inside a broker's library with a certificate error.

## 2026-09-16.81

*16 September 2026, release 81.* Chain's market list arrives on the first read after the update, not after the cached copy expires.

## 2026-09-16.80

*16 September 2026, release 80.* Every add box finds the name. Flow's add box and a new one on Short search as you type, the way Watch does: two letters and the listings that match drop down (code, company, exchange), arrows and Enter or a click pick one; the same box is now one piece of the desk for any screen that takes a name. Short takes names of its own: a name added there goes on Watch · US and its FINRA rows are read behind the page, and a watched name has its × on the row. Chain's Market is every country the desk knows, the home market first, then the United States, then the rest by name, on the chain and on any row; the desk works out the pricing path from the country, and the AI draft is told which country the chain is drawn in. Settings names the home-market broker as the home broker, not the first one saved.

## 2026-09-16.79

*16 September 2026, release 79.* A broker outside the home market sits on its own desk. A US broker connected on a desk whose home market is elsewhere shows under The US desk on Desk · Home, above the names kept by hand, with the hand-kept tiles out of the way while that book is empty; the home desk says in one line that no broker is in its market yet. Every desk block groups its digits the way its own currency does ($280,426 on an Indian home desk, never $2,80,419), and one account fills the row. Settings shows the session block the moment a daily-login broker is picked, under its keys, naming what the broker calls the key (apisession for ICICI Direct, request_token for Zerodha), so the third thing the broker asks for is visible before the first two go in.

## 2026-09-16.78

*16 September 2026, release 78.* One broker per market, each its own desk. Settings connects a broker per market (Zerodha for India, Alpaca for the US, Interactive Brokers for the world) and lists them; each is an account of its own on Desk · Home, on the desk its market belongs to (the home market's desk, the US desk, the global desk), with its own strip in its own currency, and nothing is added across desks. The home broker is the one in the reader's home market; the home market is the reader's own choice on Settings, and only follows a broker when no choice is made. A daily-login broker keeps its own login for the day. A second broker in a market already covered is refused for now, with the words saying so. Desk · Book stays the book kept by hand for anyone without a broker or a key.

## 2026-09-16.77

*16 September 2026, release 77.* Desk · Home is the home market's screen. The US desk (the US book priced live, the earnings ahead, the market pulse, the insider tape) sits on Home only where the reader has something in it: the home market is the US, a US broker is connected, a US name is on Desk · Book, or a name of the reader's own is on Watch · US. The ten names Watch · US ships with do not count, so a reader in India or Britain no longer opens on a US screen with dollar tiles; one line says how the US desk gets there when they want it.

## 2026-09-16.76

*16 September 2026, release 76.* Flow takes names. A box at the top of Flow adds a US name (it goes on Watch · US and its chain is read within a minute, the card appearing on its own), each watched card has an × that takes the name off, and the first lines say where the names come from. The economic calendar on Macro now runs sixty days and needs no key: the home market and the US in full with the low-impact noise left out, and the prints that move markets in the euro area, Britain, Japan and China; from the data provider when a key is set, otherwise from the free feed's own calendar; times shown in the reader's own clock; when the free feed is resting the calendar says so and tries again in ten minutes. The free feed is asked less often: the US grid every ten seconds in session instead of every two and a half, the home and global grids a full pass every minute and a half, so a desk (or three on one computer) stops being throttled for hours.

## 2026-09-16.75

*16 September 2026, release 75.* The drawdown view, rebuilt to be read. It is drawn from daily closes whatever the bar size (at a weekly or monthly size the chart keeps each week's or month's deepest close, so a thirty-year view stays evenly spaced and the deepest day is never lost), filled from the zero line down to the curve, the scale pinned to zero at the top, the deepest point marked on the chart with its date. The line above says where it stands: below the peak now and the days since that peak, the deepest point inside the range and its date, the longest stretch under water in the whole record and whether it is still running. A stray print in the free record (one close several times its neighbours) no longer sits in the running peak for years; the line says how many were ignored.

## 2026-09-16.74

*16 September 2026, release 74.* The Calendar reads like a calendar. This month and the next as seven-column grids, weeks as rows, today marked, each day listing the names with a dated event (a dot for the kind, the held names in the accent colour, the words on hover, a click opens the name); a header line with the counts and a legend; then the day-by-day list for the whole window beside two short lists, This week and Results ahead; the filings that landed and the macro prints below as before.

## 2026-09-16.73

*16 September 2026, release 73.* The desk's own chart is the default on every listing; TradingView's is the switch, remembered once picked. Leaving full screen no longer leaves the chart at full-screen width with the side column pushed off the page. The line under Price is short and only there when it has something to say: which TradingView symbol is on and whether their feed is delayed or end of day, or, when their chart did not load, one line saying so and that the desk's chart is showing; the Save button's tooltip carries the camera-and-paste move for their chart.

## 2026-09-16.72

*16 September 2026, release 72.* The desk's chart gets a charting screen's tools. Chart types: candles, bars, Heikin Ashi, line, area, drawdown. An Indicators menu on the panel: on the price, SMA 20, 50, 100 and 200, EMA 9, 21 and 50, Bollinger Bands (20, 2) and VWAP for intraday bars; below the price, RSI (14) with its 30 and 70 lines and MACD (12, 26, 9) with its histogram, each in its own pane; volume on or off; a log scale for the price. Every study is computed on this computer from the free feed's bars, daily studies on the full daily record so the first bars on screen already carry a settled value. The picks are remembered on this computer, the legend names what is on, and the box grows with each pane so the price keeps its room. Save chart to notes keeps all of it.

## 2026-09-16.71

*16 September 2026, release 71.* The sign follows the quote. An NSE name opened on a desk whose home market is elsewhere printed its price with the home market's sign ($715.75); the sign now follows the currency the feed names for that listing (₹ for rupees, £ or p for London, € for Euronext), and the home market's sign only where the feed names none. TradingView's frame now tells the page how it went, so the page stops guessing: their embed says when it does not carry a name (the desk's chart takes over with that reason), their first quote says the data is flowing and names the feed (BSE is end-of-day bars updated after the close; Euronext and Cboe One are delayed), and no word within twelve seconds means their data did not reach this browser (a shield or ad blocker, or no network), which the panel says in those words.

## 2026-09-16.70

*16 September 2026, release 70.* Drawings on the desk's chart. A strip under the chart: Level (one click at the price), Trendline (the first bar, then the second), Note on a bar (a click, a few words). Each drawing is kept in the vault, one plain file per listing under charts/, comes back on every visit and every range, sits on the picture Save chart to notes keeps, and has its own × in the strip; Clear all takes the file away. Nothing is written until the reader draws. A point drawn on daily bars shows on the day; one drawn on intraday bars shows on that minute, and on the daily chart at its day.

## 2026-09-16.69

*16 September 2026, release 69.* The desk's own chart, rebuilt. It is now drawn by TradingView's open-source charting library, kept inside the desk (nothing fetched, works offline): candles, line and drawdown as before, the free feed's bars at every range and bar size, MA50 and MA200 from daily closes, volume below on its own scale, a legend at the top left as the pointer moves, a crosshair with price and time, wheel and drag to zoom and pan, and the bars refilling the box whenever it changes size, full screen included. Their small mark stays on the chart, as their licence asks. Save chart to notes keeps this drawing at the screen's own sharpness. This is the chart every listing gets where TradingView's embed does not carry the exchange, and the one drawings will go on next.

## 2026-09-16.68

*16 September 2026, release 68.* The Ask box looks at the reader's chart pictures. On a listing's page the pictures kept in the notes on that name (the charts saved from the Price panel, screenshots attached to a note) go along with the question: to a key as pictures on the question, to an app on this computer as files it opens before answering; up to four, newest first, each named so the answer quotes it by title. The line under the answer says how many pictures were read.

## 2026-09-16.67

*16 September 2026, release 67.* Save chart to notes. A button on the Price panel keeps the chart as a picture in the reader's notes on that name: a clipping note, filed under the calendar quarter of the day, with the range, the bar size and the return in its one line, so it sits on the name's timeline next to that quarter's other notes, opens in Obsidian, and the Ask box can read it later. The desk's own chart is drawn straight to the picture. TradingView's chart lives in their frame, so the button says what to do: the camera on their toolbar, Copy image, then paste on the page, and the picture lands with the reader's drawings and studies on it. Undo sits next to the saved line and takes the note and its file back out. A picture pasted into the Notes editor attaches itself the same way a dropped file does.

## 2026-09-16.66

*16 September 2026, release 66.* TradingView's chart where their embed carries the exchange, checked name by name on 2026-09-17: NASDAQ, NYSE, AMEX, BSE, Euronext, Xetra, Frankfurt, Toronto, Sydney, Sao Paulo, Abu Dhabi, Jakarta, the Nordic exchanges, Zurich, Vienna, Warsaw, Tel Aviv, Milan and Madrid open on TradingView's chart; an NSE name still opens as its BSE listing; London, Tokyo, Hong Kong, Seoul, Taipei, Mexico, Johannesburg, Riyadh, Dubai, Singapore, Kuala Lumpur, Bangkok and Istanbul open on the desk's own chart, and the panel says why in one line (their embed does not carry the exchange; their own site does). The camera on TradingView's toolbar is on, so the chart can be saved with the reader's own drawings and studies. The full-screen button now says Full screen. A page opening on its default no longer remembers that default as the reader's choice.

## 2026-09-16.65

*16 September 2026, release 65.* TradingView's chart: an NSE name is handed over as its BSE listing (their embed shows NSE names only on their own site and fell back to Apple); the full-screen button works on their chart too; the panel names the symbol it handed over, and says the desk's own chart has the name when their embed does not carry the exchange.

## 2026-09-16.64

*16 September 2026, release 64.* TradingView's chart on the ticker page, and a page that never goes blank. The Price panel now shows TradingView's own chart by default (their embedded chart, their data and tools, their name on it), for any listing the desk opens: the symbol is handed over with its exchange (NASDAQ:AAPL, NSE:HDFCBANK, LSE:SHEL). A switch in the panel brings back the desk's own chart from the free feed, and the desk's chart takes over on its own when the embed cannot load; the choice is remembered. And when the free feed is resting after too many requests in a row, the ticker page shows its last full read with the time it was taken instead of an error; the error itself, when there is nothing to fall back on, now says what happened in plain words. The Watch · US add box marks free-feed listings like Watch · Home.

## 2026-09-16.63

*16 September 2026, release 63.* The chart's bar size is the reader's. Next to the range, a second row picks the bar size the way a charting screen does: 5-min, 15-min, 30-min, hourly, daily, weekly, monthly, each range offering the sizes the free feed serves for it (a day from 5-min to hourly; a month from 15-min to daily; a year daily or weekly; five years weekly or monthly) with a default per range, and the size stays as you change range while it still fits. Every range names its bars next to the return; a size too fine for the width says it is drawn as a line; the years before the daily record says quarterly. Bars at a size the page does not hold are fetched from the free feed as you pick them.

## 2026-09-16.62

*16 September 2026, release 62.* Settings, Data provider: next to the picker, where the provider lives, its plans page and its call documentation, and a table of what each of its plans opens on the desk (Basic, Starter, Premium, Ultimate), read from the provider's own plans page on 2026-09-17, with the reminder that the free record fills the three statements whatever the plan.

## 2026-09-16.61

*16 September 2026, release 61.* Models for every app in the Ask box. Codex offers GPT-6 Astra, GPT-5.6 Sol, Terra and Luna, GPT-5.3 Codex Spark and GPT-5.5 (OpenAI's own list); Gemini CLI offers Gemini 3 Pro and Flash and 2.5 Pro and Flash; Grok Build and Cursor list what your account can run by asking the app itself, read once an hour; Qwen Code takes a typed name; Kimi Code has no model switch and says so. Claude Code's list is unchanged.

## 2026-09-16.60

*16 September 2026, release 60.* Financials on every ticker page, and starter watchlists. The home-market layout (a name opened from Watch · Home) now carries the same Financials block as the US layout, so HDFC Bank opened from the watchlist shows its statements from the free record. The tabs the free record cannot fill (ratios, segments, estimates, peers, dividends, DCF) stay in view and each says in one line that it comes with a data provider. Watch · Home starts with ten names from six exchanges (NSE, LSE, Amsterdam, XETRA, Tokyo), priced by the free feed, so a desk with no broker shows the free record working in any market; Watch · US gains JPM, COST, LLY and XOM. A list you have edited is yours and is not touched.

## 2026-09-16.59

*16 September 2026, release 59.* SuperAnalyst can research the web too. A third choice in the Ask box's scope picker: Research the web too. The desk's own screens still go first; then the app or model searches the web for what they do not hold (a filing outside the desk's window, a company page, a regulator's record) and cites every page it read, links and all; a figure it could not verify is said to be unverified. It works through Claude Code, Codex and Gemini CLI on this computer, and through an Anthropic key on Settings; an app or key that cannot search is named as such when picked. Answers now show links and bold as the app wrote them, and the pages read are kept with the conversation.

## 2026-09-16.58

*16 September 2026, release 58.* Financial statements from the free record, for any listed company in any market. With no data provider, or for a name the provider does not carry, the Financials block on the ticker page now fills the income statement, balance sheet and cash flow from the free record: the last four years and four quarters, in the filer's own currency, with the lines that filer reports (a bank shows net interest income and total expenses; a retailer shows gross profit). The tabs the free record cannot fill (ratio history, segments, estimates, peers) are gone rather than empty, and the note under the table says where the numbers came from. Watch · Home names exchanges by their names rather than the free feed's codes (NSE, not NSI).

## 2026-09-16.57

*16 September 2026, release 57.* Watch · Home without a broker. A name that came in through a broker is that broker's own code (RELIND, HDFBAN), which only the broker can price; on a desk with no broker connected those rows sat blank. Now the row says broker code, no broker connected, a line above the list counts them and gives the two ways out (connect the broker on Settings, or remove the row and add the name again by company name, which picks its listing on the free feed), the add box marks each free-feed listing, and the footer explains the suffix: HDFCBANK.NS is HDFC Bank on the NSE, .BO the BSE.

## 2026-09-16.56

*16 September 2026, release 56.* The ticker page for a name the desk has no market file for. A name typed as its home code (HDFCBANK, INFY) or as words (HDFC Bank) now finds its exchange symbol on the free feed (HDFCBANK.NS) and opens that page, saying which name it matched; before, the page said no quote. And on a desk with no data provider, the Financials block no longer talks about a provider it does not have: it says the statements, ratio history, segments, estimates and peers need one, that the quote, chart, valuation and quality above come from the free record, and where a provider is set; the tabs that cannot fill are gone.

## 2026-09-16.55

*16 September 2026, release 55.* Settings, Connect: Another broker is a way in now. Picking it shows three fields for the broker (name, country, its API page) and the three ways in: paste an export into Desk · Book today, have SuperAnalyst in Build mode write the broker file from the broker's own documentation on this computer (one button puts the request in the Ask box), or send us a ticket with the name. What you type stays on the page between visits. The brokers readers have already asked about, with the way in for each, follow below.

## 2026-09-16.54

*16 September 2026, release 54.* Settings, Your AI: each app card now says whether you are signed in, in the app's own words. Claude Code, Codex and Cursor are read from their own status command when the screen opens and every few seconds after you press Sign in, so the card turns to Signed in on its own once the browser sign-in completes. Gemini CLI, Kimi Code, Grok Build and Qwen Code have no status command, so a Check button on every card asks the app a one-word question and reports what came back.

## 2026-09-16.53

*16 September 2026, release 53.* The Ask box: Stop, conversations kept, and a model picker. Ask turns into Stop while an answer is on its way, and Stop ends the app run on this computer, so a question to an app that is not signed in no longer locks the box. Every conversation is kept on this desk (never in the vault) and comes back when you reopen the box, change screens or reload; a picker in the box reopens an old one, + starts a new one, × deletes the one open, and the list's last line deletes them all. A third picker chooses the model: the app's own default, the names it accepts (Claude Code carries the Anthropic list), or a name you type; an app without a model switch says it picks its own.

## 2026-09-16.52

*16 September 2026, release 52.* Ticker page chart: every range draws candles. 1D is five-minute bars, 5D fifteen-minute, 1M to 1Y daily, longer ranges weekly or monthly, and the candle width follows the bar count, so a month no longer shows twenty-two slabs and a week no longer falls back to a line. The bar size is written next to the range.

## 2026-09-16.51

*16 September 2026, release 51.* SuperAnalyst reads the whole desk, sizes to taste, and can build. Three changes to the Ask box. It is any width now: drag its left edge, or step through a third, half and the whole screen with one control, and the width is remembered, so the screen behind stays in view while you ask. It reads the whole desk, not one screen: the screen you are on goes first, then the screens the question points at (a name you mention brings its ticker page and your notes on it; the words you use bring short interest, the 13F holders, the calendar, the macro cards, the book), and SuperAnalyst holds a map of every screen and can ask the desk for one more before answering, so a question asked on Risk about a name's filings is answered from the Calendar rather than with "ask on that screen". And a second picker, Research or Build: Research, the default, reads the desk and changes nothing; Build hands your request to the app on this computer, run in the desk's own folder with its edits allowed, so it can change the desk itself (a column, a screen, a plugin, a chain) and says what it changed, file by file, and whether a restart is needed. Build works through Claude Code, Codex, Gemini CLI and Qwen Code; a key can only answer, and the box says so. The book, the watchlists, the keys and the vault are the reader's and are never rewritten beyond the edit asked for.

## 2026-09-16.50

*16 September 2026, release 50.* SuperAnalyst. The desk's AI has its name back: the sidebar says Ask SuperAnalyst, the box says SuperAnalyst, an AI, reading whichever screen you are on, and its first line says so again in words. The picker that chooses who answers is in view on every desk now, on its own line under the name: the key on Settings, then every app the desk can hand a question to (Claude Code, Codex, Gemini CLI, Kimi Code, Grok Build, Qwen Code, Cursor), the ones not on this computer greyed with the reason, so a reader sees what else could answer and what a sign-in would add. The Terminal door ships with the desk: a fresh install has every app in the picker without bringing a plugin in, and a copy of the door brought into the vault still takes the shipped one's place.

## 2026-09-16.49

*16 September 2026, release 49.* The Calendar, and the Notes screen rebuilt. A new screen under Intelligence, Calendar: every dated event on every name you hold or watch, in any market, from the free record and reread by the desk on its own every six hours: results dates (the company's own once announced, an estimate from past reporting dates until then, and the row says which), ex-dividend and payment dates, the filings that landed at the SEC on your US names in the last thirty days with a link to each, the home market's results calendar where the desk has one, and the macro prints ahead when a provider is connected. Yahoo's free summary serves any exchange; Nasdaq's own site is the second source for a US listing on the days Yahoo says too many requests; a name that could not be read is named on the screen and retried within fifteen minutes. A results date lands on Tasks by itself, as before. Notes is one screen again, laid out like a document: on the left the index of the vault (what is due, what the desk saw, every name with its status and count, every project and subject), on the right every note as a table with four plain filters, or the note you opened, or the editor with its live blocks; a name's line opens its timeline with New note, Bring a file in and Tasks on it one click away. The row of filter pills, the Explorer toggle and the welcome cards are gone. The sidebar button says Ask AI, the box says an AI is reading the screen, and its two header controls are drawn icons that read at a glance.

## 2026-09-16.48

*16 September 2026, release 48.* Every country is a home market. The Home market list on Settings now carries every country: India and the United States with the full public record, about fifty countries whose exchange the free feed carries with their quotes, session hours in the exchange's own time zone and the index Risk measures against (the United Kingdom, Japan, Germany, Brazil, Australia, the Gulf and more), and every other country with its currency and the world index. A connected broker still sets the country for you. Under Another broker, a reader whose broker the desk does not know names it and opens a ticket with the details filled in; nothing is sent until they press the button there. A Feedback door sits in the sidebar of every screen for the same reason: a wrong row, a misread number, a broker or a market the desk should know, one ticket each, with the screen and the version already written in. The Ask box takes the whole screen on one click and comes back on the next, and remembers which you chose.

## 2026-09-16.47

*16 September 2026, release 47.* Desk · Book, read screen by screen. The tiles sit one row per currency, the largest book first, so a second currency no longer leaves one tile stranded on a line of its own. A flat day reads flat: a price that has not moved shows 0.00% in grey rather than +0.01% in green, on the book, the home screen, the watchlists, the ticker page, the chain and the commodities board alike, and the single-precision noise in Yahoo's daily closes (1.15 arriving as 1.1499999761) is rounded away at the feed so no zero move is ever reported as a move. Fractional shares carry three decimals here as on the home screen. The positions header no longer repeats the feed note printed above it, the currency box and the symbol box are wide enough for their own hints, Enter saves from the shares box and the cash box, and the two notes that named a file on disk say what the book is instead. The installer's first download try is quiet, so a reader whose install fell through to the mirror never sees an error from a download that succeeded.

## 2026-09-16.46

*16 September 2026, release 46.* The front page and the docs carry the GitLab mirror beside GitHub at the top, so either home of the code is one click away.

## 2026-09-16.45

*16 September 2026, release 45.* The desk has a second home. The repository is mirrored on GitLab (gitlab.com/shikshan-nivesh/greeksoup) with every push, and the install line and the update check read from the mirror whenever GitHub does not answer, so an outage or a review on one side never stops a new install or an update. The release script refuses to tag a commit that does not carry the version it is publishing.

## 2026-09-16.44

*16 September 2026, release 44.* Desk · Home, read screen by screen. One hand-kept book: the separate US file behind the US panel is folded into Desk · Book on the first start (a line already on Desk · Book wins, the US cash joins the USD cash, a copy is kept under cache/previous), and the panel, the earnings tags, the insider, options, short-interest, activist and Congress screens and Risk all read the US names on Desk · Book from now on; the author's own mandate line and the decided-by column are gone from the panel. Every holding's day change is the desk's own, against the last session's close: a broker's own field can read zero after the close, so Desk · Home and Watch disagreed on the same name. The running tape names the account only when there are two or more. The Updated strip shows only for the version now running, so a browser that never saw an old update's strip is not shown it weeks later. Earnings estimates carry two decimals, and fractional shares three.

## 2026-09-16.43

*16 September 2026, release 43.* The line is back where it belongs: For investors who refuse to settle, under the headline on the front page, on the docs home and in the docs footer.

## 2026-09-16.42

*16 September 2026, release 42.* Three corrections to what the charts and the quotes say. A history chart on Commodities and Macro places every point at its date, so a year is the same width wherever the series is dense; the free series are daily for the last two years and weekly or monthly before, and the old axis gave 2025 a third of the chart and 2019 a sliver; the years or months are marked along the bottom. A ticker's free history is daily for ten years, since Yahoo's all-time answer is quarterly whatever is asked and the one-year chart of a name with no data key was four points spread over forty years; the years before those ten are quarterly, and a range that reaches into them is drawn as quarterly bars. The day change on a free quote is against the last session's close; it was against the close five sessions back on every Watch grid, every Desk · Book line and the Global list. Every commodity card's sparkline covers the same one year.

## 2026-09-16.41

*16 September 2026, release 41.* The docs wear the landing page's system: Geist and JetBrains Mono only, the serif and the italic eyebrows gone, hairlines in place of cards, chips and shadows, the section index as a list that opens on a hairline, the broker facts as a two-column table, the steps numbered in mono, and the same top bar as the front page, with Install, Security, the theme switch, the GitHub mark and the Install button; the tagline is off the docs home and the footer.

## 2026-09-16.40

*16 September 2026, release 40.* The landing page's top bar is down to three words, Install, Security and Docs, with GitHub as its own mark beside the Install button; the Screens, Data and Keys links are gone, since the page reads top to bottom on its own.

## 2026-09-16.39

*16 September 2026, release 39.* Ask · your AI is the one lit button in the sidebar's foot, orange, so the desk's centre is the first thing a new reader's eye lands on. The recording on the landing page is thirteen seconds on a loop, no voice: ten screens with a crossfade and a slow push into each, playing on its own where the page allows it, mp4 and webm, three megabytes each.

## 2026-09-16.38

*16 September 2026, release 38.* Yahoo's free quotes hold up through a burst: Yahoo throttles by the pair of your address and the browser string a request carries, so when one string is refused the desk moves to the next and stays there, instead of going quiet for five minutes; the ticker page and the free book prices come back sooner on a busy afternoon. The landing page carries a recording of the desk, eighty seconds, no voice, ten screens as they open, with a play button on a poster; the orange is back where it belongs, in the hero, on the buttons, and on the one loud block about what the desk talks to.

## 2026-09-16.37

*16 September 2026, release 37.* The landing page's top carries the one-line install as a card beside the headline again, with the four things the line does; What it needs is a map of the fifteen screens, each tile marked by what lights it (no key, a broker key, and where a feed key adds columns), with the three counts beside it; Install shows what the line prints, step by step, beside the line itself. The example plugin is no longer on the published list: a desk carries only what does something for you, and the example stays in the repository for anyone writing a plugin.

## 2026-09-16.36

*16 September 2026, release 36.* Four more apps you may already pay for answer the Ask box: Kimi Code, Grok Build, Qwen Code and Cursor join Claude Code, Codex and Gemini CLI on Settings under Your AI, each found on the computer itself, each with Use it for Ask and Sign in (Grok Build answered through the door on the author's computer; the other three follow their makers' documented one-shot flag). The Terminal door no longer adds a page of its own, since everything about it lives on Settings; a shipped plugin you installed is brought up to the version that ships with a release when the desk starts, so that change reaches an installed copy on its own. The example plugin says on its first line that it is an example and how to remove it. Your AI in the docs and the FAQ answer the question of whether running Claude Code or Codex from the desk is allowed and how the usage is counted, with what each maker says as of 15 June 2026. The landing page carries a sliding Works with band, names and kinds, no logos: the seven apps, the labs, the local models, the six brokers, the public record, the data provider, the two markets.

## 2026-09-16.35

*16 September 2026, release 35.* The landing page is rebuilt lean: seven sections instead of twelve, two typefaces instead of four, no icons, pills, cards or tilting frames; the fifteen screens are a list that drives one large screenshot beside it, the three figures drawn from the desk's own data sit flat on hairlines, keys are a three-column table, install is one line with the two other ways folded under it, what the desk talks to and what can go wrong share one section, and the closing section carries the Shikshan Nivesh mark and the edition without a second lockup. About forty percent shorter, nothing said on it dropped.

## 2026-09-16.34

*16 September 2026, release 34.* The repository is github.com/shubhamsborkar/greeksoup now, and every address in the desk, the installers, the docs, the landing page and the README follows it (the old address keeps redirecting, so a desk on an earlier version still finds its updates). The README banner is the hero: the mark large on the left, the wordmark on the right over one line, your desk, your computer, your keys; the same composition sits behind the project's covers on GitHub, X, Substack and LinkedIn. The Community section carries where we post: GreekSoup and Shikshan Nivesh on LinkedIn, ShikshanNivesh on X and Substack.

## 2026-09-16.33

*16 September 2026, release 33.* The repository reads like the project it is: the README opens with the GreekSoup mark and wordmark, a row of live badges (checks, the current release, Python, the three systems, the licence, the newsletter), one paragraph on what stays yours and a link row to the site, the docs, the screens, security, releases and the FAQ; a table of where to read next and a Community section at the end; the screen count is fifteen everywhere and Notes has its line; the install lines here and in the docs are the short greeksoup.ai ones. AGENTS.md at the root (with CLAUDE.md and GEMINI.md pointing to it) tells any AI agent opened in the desk folder what the desk is, what belongs to the reader and must not be overwritten, and how to start, check, test and roll back. Every release is now tagged and published on GitHub's Releases page with the same line the update strip shows.

## 2026-09-15.32

*15 September 2026, release 32.* Two guards on every request, so a web page you visit cannot read your book or post to Settings: a request whose Host is not this computer is refused (DNS rebinding), and a request from a browser that is not the desk's own page is refused (a cross-site read or post); programs on your own computer are let through as before; the Security page is rewritten around what can go wrong and what the desk does about each thing, with the honest limits and the answer to running it on a server; new docs pages for Your lists, Chains and Your computer or a server; the landing page and the docs carry every screen and setting shipped this week, with fresh screens

## 2026-09-15.31

*15 September 2026, release 31.* The apps card under Your AI reads the computer itself, so Claude Code, Codex or Gemini CLI show as found before any plugin is in, and Use it for Ask brings the Terminal door in on its own when it is not there yet

## 2026-09-15.30

*15 September 2026, release 30.* An AI you already pay for, without a key: Settings, under Your AI, now shows the apps found on this computer (Claude Code on a Claude subscription, Codex on ChatGPT, Gemini CLI on a Google account), each with Use it for Ask and Sign in, which opens the app's own sign-in in a terminal window and your browser; the desk never sees the login, it hands the app a question and reads the answer; the Ask box and the chain draft then answer through that app by default, and the picker on the Ask box names the app and what it runs on

## 2026-09-15.29

*15 September 2026, release 29.* Settings is three short tabs instead of one long page: Connect (broker, data, your AI), Your desk (screens, where the vault lives, how you invest, journal, this desk, backups, help) and Plugins; a link into Settings opens the right tab; and the words on the screen are the reader's, so an endpoint is where the AI answers and a request format is how it is spoken to

## 2026-09-15.28

*15 September 2026, release 28.* A startup guide sits bottom right on the first opens: five steps with a tick each, where your research lives (keep it beside the desk, put it in Documents › GreekSoup, or in a folder iCloud Drive, Google Drive, Dropbox or OneDrive already syncs, chosen right there), connect a broker or start with the paper book, pick your AI, make your first list your own, save your first note; a step ticks itself when the desk can see it is done, Done hides the guide, and it comes back from Settings under This desk or from the ⌘K palette

## 2026-09-15.27

*15 September 2026, release 27.* Wherever a name appears on any screen, a small ⋯ on hover carries the next thing to do from right there: open it, add it to a watchlist, a note on it, a task on it, put it on one of your chains (pick the chain and the layer), or ask your AI about it; one menu for every screen, so the reader leaves the screen they are on as rarely as possible

## 2026-09-15.26

*15 September 2026, release 26.* Risk measures your home book against the index you choose: type any index symbol in the top bar of Risk (^NSEI, ^GSPC, ^FTSE, ^N225) and a name for it, and Follow the market is the way back; every screen's words were read again for the reader, so the notes and footers no longer point at file names or the author's own folders, and the Funds and Capitol screens say where their lists are kept

## 2026-09-15.25

*15 September 2026, release 25.* Every list a screen runs on is yours: Funds, Capitol, Macro and Commodities carry a Your list button in the top bar (the options tape on Desk · Home has it on its panel) that opens a drawer to add a row, edit one, remove one with Undo, and bring the shipped starters back; the shipped funds, members, macro series, commodities and tape names are starters, an edited starter becomes your copy in place, and your rows live in your research vault beside your notes, so they sync, back up and restore with them

## 2026-09-15.24

*15 September 2026, release 24.* An update never loses saved work: every file you own (your chains, Desk · Book, the hand-kept US book, your watchlists, your alert rules) now carries a format number; when a version changes a file's shape the desk brings the file up at the next start after keeping a copy under cache/previous, and the banner says which file and where the copy is; a file written by a newer desk (a vault synced from another computer) is left as it is and named; and the release script lists every file readers may hold edited copies of before a version ships

## 2026-09-15.23

*15 September 2026, release 23.* The .22 update carried its notes but not its code (the manifest was made before the new files were staged), so a desk that took it shows the old Chain screen with the new version stamped; this release carries the whole of .22, and the release script now refuses to write a manifest while a file that would ship is not staged

## 2026-09-15.22

*15 September 2026, release 22.* The Chain screen is yours: press + New chain, describe the industry, the product or the company at its centre, and your AI drafts the first map, upstream to downstream, every layer saying what it buys and what it sells, the listed names under each with a receipt (in a filing, on the record, or reported) and the named supplier to customer links; every line lands in a form you keep, change or drop, and nothing is saved until you press Save; chains live in your research vault beside your notes, so they sync, back up and restore with them; the chains that ship are starters, put one away or make it yours, and Bring the starters back is the way back; Delete keeps a copy and Undo brings it back; and the top bar and the group rows on Funds, Macro and Watch now follow the light theme instead of staying dark

## 2026-09-15.21

*15 September 2026, release 21.* Two computers with no service and no account: Settings gains Where the vault lives, point it at a folder inside a drive you already sync (iCloud Drive, Google Drive, Dropbox, OneDrive, Syncthing) and the desk moves the vault there and reads from it from then on; the desk on your other computer pointed at the same folder adopts the vault it finds and folds its own in, an identical file dropped, a differing one kept aside; Bring it back is the way back; backups and restores follow the vault wherever it lives

## 2026-09-15.20

*15 September 2026, release 20.* Desk · US lives on Desk · Home now, for every reader wherever the home market is: the hand-kept US book, the earnings countdown, the market pulse and the insider tape sit under the broker book, because a reader in any market holds and watches US names; the separate screen is gone, an old bookmark to it lands on Home, the Ask box on Home reads the US panels too, and the landing page's fourteen screens now include Notes

## 2026-09-15.19

*15 September 2026, release 19.* Restore a backup from Settings: the zip's files go back into place, on this copy or a fresh one on another computer, any file the restore would change is kept aside first under cache/previous so the restore can be undone, and the message says what was written, what was already the same and where the changed files went; the backup itself now carries the whole research vault, plugins included

## 2026-09-15.18

*15 September 2026, release 18.* Plugins, and the terminal door as the first one: a plugin is a folder in data/research/plugins that adds a screen to the sidebar, blocks a note can carry, or a door for the Ask box; Settings shows what each one adds and what it talks to, brings one in from the list at greeksoup.ai, a folder or a zip, and removes it in one click; the terminal door lets the Ask box answer through the coding agent already on this computer (Claude Code or Codex) with the same screen data and your notes, no key needed, chosen from a picker at the top of the box; a second plugin, Hello, is the smallest one there is, to be copied; the sidebar fits its groups without scrolling

## 2026-09-15.17

*15 September 2026, release 17.* Live blocks in a note: three backticks, the word desk, one line naming a block, and the desk draws it on the note's page while any editor shows it as code (quote, chart, watch, commodity, status, notes, tasks, timeline, book), reading what the screens already hold and never waiting on a feed; a note that is mostly blocks is a dashboard, and an example one ships; a note that names a listing is a stock note unless it says otherwise, and an attached file follows its note's name into the right folder (a file with no subject used to land in files/note)

## 2026-09-15.16

*15 September 2026, release 16.* The GreekSoup mark, on everything: the sidebar, the tab icon of every screen, the docs and the landing page, in the Shikshan Nivesh family (a prompt caret and three rising bars); and the Notes screen gains an Explorer view, the vault as folders, one per name with everything about it inside, plus commodities, sectors and themes, projects, the journal's days, the tasks and any file on no note yet, next to a first-class Attach a file button and a start-here card that shows the three ways in

## 2026-09-15.15

*15 September 2026, release 15.* Tasks that make themselves, and tasks you make: a results date for a name you hold, watch or are researching becomes a task on its own and goes when the date passes; every answer in the Ask box gets Save as task beside Save as note; a line typed on the Tasks screen or a listing's page, or a checkbox inside any note, lands on the same list, with a due date and a category; tasks live in data/research/tasks.md as plain checkboxes, a task due today or overdue shows in the alert bar, and ticking one is a moment the journal sees

## 2026-09-15.14

*15 September 2026, release 14.* The journal that fills itself: the moments the desk sees (a name entering or leaving Desk · Book or a watch grid, a status change, a note or a file saved, an answer kept) become lines in one plain file per day in data/research/journal, with room for your one-line why; you choose on Settings whether the desk asks each time (This time, Always, Not now, Never, right where you are, with a why box on a decision), always writes, or never does; held moments wait in the Journal on the Notes screen rather than disappear, and your own lines go in from the same place

## 2026-09-15.13

*15 September 2026, release 13.* Where a name stands, and its timeline: every listing's page carries a status (watchlist, researching, thesis built, invested, exited), two of which the desk sees for itself from your books and watch grids, and your own word wins and is kept with every change dated; the Notes screen filters on status; and a Timeline under your notes on a listing's page, and on the Notes screen when you look at one name, lays out everything about the name by period and date, status changes included

## 2026-09-15.12

*15 September 2026, release 12.* The desk reads what is inside the files you bring in: a PDF page by page, a spreadsheet sheet by sheet, a Word file or a presentation by paragraph, read once and locally into data/research/index; the search box on the Notes screen and Command K find a phrase that lives only inside an annual report, and the Ask box on a listing's page reads your notes and your documents about it along with the screen's numbers; a note with a file says how many pages were read, or that the desk is still reading, or that the kind of file has no text to read

## 2026-09-15.11

*15 September 2026, release 11.* The research vault: notes move into data/research/notes (once, on the first start, nothing left behind) and files you bring in live beside them in data/research/files, one folder per subject; a document is a note with a file attached, so an annual report dropped on a listing's page, a model or a screenshot becomes a Document, Model or Clipping note that takes a period, joins a project and shows on the listing's page, with the file opening in a new tab; removing a file or deleting its note asks whether the file stays, a file no note points at is listed on the Notes screen with give-it-a-note and delete beside it, and a file moved away by hand shows as missing rather than vanishing; the backup takes the whole vault

## 2026-09-15.10

*15 September 2026, release 10.* Hiding a screen is no longer a one-way door: a hidden screen stays in the sidebar under Hidden with Show one click away, hiding shows an Undo where you clicked, and Settings still lists every screen; a reader hid Desk · Book and could not find the way back

## 2026-09-15.9

*15 September 2026, release 9.* Notes say what they are about and which quarter: a note is about a listing, a commodity, a sector, the macro picture or nothing in particular, names its subject when that is not a listing, and carries the period it researches (Q2 FY26 style), so the Notes screen filters on any of the three; every answer in the Ask box gets a Save as note button that files the question and the answer under the name and the period you set, and nothing is saved unless you press it; the Ask box on Commodities and Macro reads your commodity and macro notes; the card at the top of every note is valid YAML, so Obsidian shows each field as a property; a fourth example note shows a commodity note with a period

## 2026-09-15.8

*15 September 2026, release 8.* Notes: the research you write, kept as plain Markdown files in data/notes, one per note, each linked to the listings it names, the project it belongs to and the notes it links to; a listing's page shows your notes on it and the other names connected through them, the Ask box reads them, and an AI agent or Obsidian works on the same files; a note takes a company's name and finds the listing for you

## 2026-09-15.7

*15 September 2026, release 7.* The desk adapts to whoever installs it: any screen can be hidden with one click in the sidebar or in Settings and brought back the same way, the US desk shows only when the home market is the United States unless you say otherwise, Desk · Book takes a company's name and finds the listing for you, arrives with a few example lines that Clear the book removes in one click, and totals the currency most of the book sits in first; the Burry box on Funds is gone

## 2026-09-15.6

*15 September 2026, release 6.* Windows needs no administrator: the start-at-login entry is a task made for your user only, with no time limit, and when a work or school PC refuses that with Access is denied, a shortcut in your own Startup folder takes its place; a reader hit that refusal on the first try. Running the install line again on an installed desk now brings it up to date first and never waits on a hidden prompt

## 2026-09-15.5

*15 September 2026, release 5.* Stop Desk and Uninstall Desk on Windows now stop the desk they belong to: the desk writes its own process number into its folder once it holds its door, and the stop looks there first, then at whatever answers on that door when it or the launcher that started it runs from this folder; the first full Windows run had reported the desk stopped while it went on answering

## 2026-09-15.4

*15 September 2026, release 4.* The desk answers on both of this computer's own addresses, which is what a fresh Windows machine showed was needed: Windows reads the name localhost as the IPv6 address first, so a desk listening only on the IPv4 one could look absent while it was running perfectly well; neither address is reachable from another machine

## 2026-09-15.3

*15 September 2026, release 3.* The Windows install can run unattended, so a fresh Windows machine can install the desk, open every screen and remove it again on every change, which is how Windows gets tested without a Windows PC in the room

## 2026-09-15.2

*15 September 2026, release 2.* Uninstall is exact about which desk it removes: the folder you name always wins, a desk is closed only when the program answering on its own door number is working inside that folder, and the start-at-login entry is left alone unless it names that folder, so a reader with a second copy of the desk keeps it untouched; the check tells the same difference, and says so when the entry it finds belongs to another copy

## 2026-09-15.1

*15 September 2026, release 1.* The site tells a machine what it holds: a sitemap of every page, a robots file that says everything here is open to read, and an llms.txt, the plain-text index an answer engine or an AI agent reads instead of the HTML; every docs page carries its own canonical address and share card; the landing page carries the desk's own description and the ten questions readers ask in the shape a search engine parses; the check that runs on every change now knows the difference between an installed desk and the repository, and holds the Ask box to its reads, its addresses and the line that keeps it from telling anyone what to buy

## 2026-09-15

*15 September 2026.* The Ask box: Ask · your AI at the bottom of the sidebar (or ⌘I) opens a box on every screen; your question goes with that screen's own numbers, and the how-you-invest lines from Settings, to the AI you set there, and the answer comes back in the box with the addresses it read; the box keeps the conversation while the screen is open; long price histories are shortened before they go so a screen fits in one question; it describes what the numbers show and is told never to say buy, sell or hold; nothing is sent anywhere but the one address you chose, and a model on this computer never leaves it

## 2026-09-14

*14 September 2026.* What a finished desk carries around the desk itself: a check you run in the folder (python doctor.py) that prints what your agent needs and nothing private; an uninstall that stops the desk, removes the start-at-login entry, saves your lists to the Desktop and asks before deleting the folder (Uninstall Desk on Mac and Windows, or one line); the updater keeps the files each update replaces for the last three versions and one line puts them back (python updater.py rollback); a written security page (what the desk talks to, where keys live, how to report), a contributing guide, issue templates for a bug, a broker and a market, a pull request template, and a check that runs on every push holding every broker and market file to its contract; docs gain Setup (your AI, data providers, data sources), FAQ, What it talks to, If something is wrong, and Project (releases, contributing, security); the landing page gains a works-with grid and a what-it-talks-to section

## 2026-09-13.8

*13 September 2026, release 8.* Nothing in the desk assumes one broker or one country any more: a broker file is read for what it has (holdings and cash always; ticks, futures, margin, chains and a symbol master when the broker serves them), and the market the broker trades in supplies the session, the index, the currency, the results calendar, the filings and its own macro cards from a file in the new markets folder (India and the United States ship, any other is one short file to a written contract); Settings gains a home-market choice for readers with no broker; the daily-login helper files are gone, Settings does that job

## 2026-09-13.7

*13 September 2026, release 7.* Your broker, your data provider, your AI, all picked from a list with nothing assumed: six brokers connect as the desk comes (Alpaca, ICICI Direct, Interactive Brokers, Tradier, Trading 212, Zerodha), read-only, with the currency and market hours following the broker; any other broker or data provider is one file your agent writes to a written contract; the AI settings carry the request shape the endpoint speaks (OpenAI chat or Anthropic messages) with presets for fourteen providers and local models

## 2026-09-13.6

*13 September 2026, release 6.* Settings grows three sections: how you invest (style, what you look at first, sectors, risk, holding period, your own words), carried on the agent page so any AI reading the desk answers you and not a stranger; your files, with a one-click backup of the data folder; and what to do when something is wrong

## 2026-09-13.5

*13 September 2026, release 5.* A Settings screen inside the desk: the broker keys and the daily token, the data key with a check of what your plan answers, your own AI key with a test, the address that lets any AI agent on your computer read the desk, and switches for starting with the computer and for automatic updates; no file to edit any more

## 2026-09-13.4

*13 September 2026, release 4.* After an update the page reloads itself once the desk is back, and only names the folder to open if the desk has not come back in ninety seconds

## 2026-09-13.3

*13 September 2026, release 3.* Desk · Home now says how to connect a broker (by hand on Desk · Book, the shipped adapter, or any broker through your agent) and speaks of the exchange rather than one country's exchange

## 2026-09-13.2

*13 September 2026, release 2.* One-line install for Mac, Linux and Windows (finds or installs Python, downloads the desk, sets it to start with your computer, opens it); the install paths rewritten for a reader with no AI agent

## 2026-09-13.1

*13 September 2026, release 1.* The desk is now called GreekSoup: the one-person equity research desk, in the sidebar, the page titles and the README; nothing else changed

## 2026-09-13

*13 September 2026.* The desk now looks at GitHub once a day and, when a newer version exists, says so on every screen and brings it in with one click

## 2026-09-12

*12 September 2026.* The US names on the Commodities screen carry their filed figures, 58 of 59, each with the document it came from; three tickers corrected (Barrick is B, Solaris Energy Infrastructure is SEI, US Steel removed)

## 2026-09-09

*9 September 2026.* The Commodities screen (51 commodities, the industries each one squeezes and helps, the names mapped to them from their filings, two new alert rules) and Desk · Book, the hand-kept portfolio for readers with no broker and no feed

## 2026-09-03

*3 September 2026.* First public version, twelve screens
