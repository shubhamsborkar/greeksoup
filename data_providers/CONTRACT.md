# Data providers: what the desk asks for, and the shape it expects back

The desk runs keyless on the public record. A data provider adds the parsed reads below. One provider ships today (Financial Modeling Prep, in `server.py`, `insiders.py` and `freefeed.py` through `fmp_get`); any other provider is a file in this folder that answers the same questions, written by the reader's agent from that provider's documentation, and the Settings screen already keeps the provider's name, key and address for it (`DATA_PROVIDER`, `DATA_API_KEY`, `DATA_BASE_URL` in `.env`).

## The reads

Every function returns plain Python (lists of dicts, numbers as floats, dates as `YYYY-MM-DD` strings) or `None` when the provider does not have it. A read the provider cannot answer returns `None`, and the screen says so in one line; it never raises.

| Function | Used by | Returns |
|---|---|---|
| `quote(symbol)` | ticker page, US watch grid | `{"price", "prev_close", "day_pct", "market_cap", "volume", "name", "exchange", "currency"}` |
| `profile(symbol)` | ticker page, sector lookups | `{"name", "sector", "industry", "country", "description", "employees", "ceo", "website"}` |
| `income(symbol, period, limit)` | ticker page statements | list, newest first, each `{"date", "period", "revenue", "gross_profit", "operating_income", "net_income", "eps_diluted", "shares_diluted"}`; `period` is `"annual"` or `"quarter"` |
| `balance(symbol, period, limit)` | statements | list of `{"date", "period", "cash", "total_assets", "total_debt", "total_equity", "shares_outstanding"}` |
| `cashflow(symbol, period, limit)` | statements, quality | list of `{"date", "period", "operating_cf", "capex", "free_cf", "dividends_paid", "buybacks"}` |
| `ratios_ttm(symbol)` | valuation panel | `{"pe", "ps", "pb", "ev_ebitda", "roe", "roic", "net_margin", "debt_to_equity", "dividend_yield"}` |
| `estimates(symbol, limit)` | estimates panel | list of `{"date", "revenue_avg", "eps_avg", "analysts"}` |
| `segments(symbol)` | segments panel | list of `{"date", "segments": {"name": revenue, ...}}` |
| `peers(symbol)` | peers panel | list of symbols |
| `dividends(symbol, limit)` | dividends panel | list of `{"date", "amount"}` |
| `news(symbol, limit)` | news panel | list of `{"date", "title", "url", "source"}` |
| `history(symbol, days)` | 50 and 200 day columns, risk | list of `{"date", "close"}` |
| `insiders_latest(limit)` | market-wide insider tape | list of `{"symbol", "name", "insider", "title", "type", "shares", "price", "date"}` |
| `senate_latest(limit)` | Capitol | list of `{"symbol", "member", "type", "amount", "date", "disclosed"}` |
| `shares_float(symbol)` | Short | `{"float_shares", "outstanding"}` |
| `search(query)` | the command palette | list of `{"symbol", "name", "exchange"}` |

## The file

`data_providers/<name>.py` with `META = {"label": "Provider name", "docs": "https://..."}` and any of the functions above; the key comes from `os.getenv("DATA_API_KEY")` and the address from `os.getenv("DATA_BASE_URL")` (blank means the provider's default). Missing functions are the same as returning `None`. Rate limits are the file's to respect: a refusal from the provider becomes `None`, never a crash, and a per-call cache lifetime keeps the free tiers happy.

Wiring the file in is the second half of the job and it is the agent's: every `fmp_get(...)` call in the desk is one of the reads above, so the agent replaces those call sites with the provider layer's functions once its file exists. This contract exists so that job has a fixed target.
