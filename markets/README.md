# Markets: one file per home market, all from the public record

A broker file says which market its accounts trade in (`META["region"]`). The matching file in this folder supplies what that market's public record offers, and the desk shows it on Desk · Home, Watch · Home, Risk, Macro and the home ticker page: the session hours, the index Risk measures against, the currency, the Yahoo symbol for an exchange symbol, and where the file has them, the exchange's results calendar, its filings, and the market's own macro cards.

Shipped: India (`in.py`) and the United States (`us.py`) with the full record, and every other country from the table in `world.py` (currency; where Yahoo carries the exchange, its suffixes, the session in the exchange's own time zone and the benchmark; else the world index). `HOME_MARKET=<iso2>` in `.env` picks one by hand; a broker's `region` overrides it. A file in this folder, named in `FILES`, takes over from the country's table row.

## Writing one for another market

Copy `us.py`, fill in `META`, and add the file's name to `FILES` in `__init__.py` (it takes over from the country's table row). Then give the broker file for that market the same `region`.

```
META
  id               the region code, matching the broker file ("uk", "au", "de" ...)
  label            "United Kingdom"        plain words, shown to the reader
  currency         "GBP"    symbol "£"     locale "en-GB"
  exchanges        ["LSE"]                 the first is the default for a new watch name
  session_label    "LSE"                   what the market-open dot says
  benchmark        "^FTSE"                 Yahoo symbol of the index Risk measures against
  benchmark_label  "FTSE 100"
  econ_country     "GB"                    the economic calendar's country code
  filings          ""                      where the ticker page's results come from, if any
  units            ""                      the unit those filings report in

is_open(now=None)        -> True during the regular session, in the computer's local time
ysym(symbol, exch=None)  -> Yahoo's symbol for an exchange symbol (RR on LSE -> "RR.L")

optional
macro_series()           -> [(id, label, unit, group, fetch)]; fetch() returns [(date, value)]
                            ascending, and the Macro screen draws the card
macro_cards()            -> cards the file builds itself (see in.py's repo rate)
results_calendar(symbols)-> {"rows": [{"symbol", "company", "date", "purpose"}], "skipped": n}
fundamentals(symbol)     -> {"quarters": [...], "shareholding": [...], "announcements": [...]}
                            for the home ticker page, or None when the source is down
commodities_local(cards) -> attach the market's own price lines to the Commodities cards
                            (c["local"], a list of {"kind": "local", "tag", "label", "short",
                            "detail", "note", "level", "unit", "day_pct", "ts", "stale"}) and
                            return True when anything was attached; keyless, from the public
                            record (see in.py: the benchmark mandis, the Rubber Board)
```

Keep the file to public sources, date-stamp anything scraped, and let a failed fetch return the last good value rather than nothing.
