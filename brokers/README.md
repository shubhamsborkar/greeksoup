# Brokers: one file each, all read-only

The desk reads a broker account through one file in this folder. The reader picks the broker on the Settings screen, pastes what that broker hands out, and Desk · Home fills. Nothing here places an order.

Shipped: Alpaca, ICICI Direct (Breeze), Interactive Brokers (Flex Web Service), Tradier, Trading 212, Zerodha (Kite Connect). Each file's docstring names the documentation it was written from.

## Writing one for another broker

Copy the closest shipped file, keep the same function names, and add the file's name to `REGISTRY` in `__init__.py`. The desk needs:

```
META
  label          "Your Broker"
  where          "United States" / "India" / "worldwide" ...  (plain words, shown to the reader)
  region         "us" or "in": which ticker page a holding opens on
  daily_login    True when the broker wants a fresh login every trading day
  docs           the broker's own API page
  how            one sentence: where the reader gets the keys
  fields         [{"env": "MYBROKER_KEY", "label": "API key", "secret": True}, ...]
                 add "switch": True for an on/off field, "required": False for an optional one,
                 "hint" for a line under the box
  token_hint     (daily login only) what to paste after the login
  token_param    (daily login only) the query parameter the redirect carries

connect(cfg, token=None) -> client          cfg = the fields, read from .env; raise
                                             BrokerError("plain words") when the broker says no;
                                             return None when a daily-login broker has no token yet
label(client)            -> "A/C ··1234"     last four characters of the account, never a name
equity(client)           -> [row, ...]
funds(client)            -> {"cash": float, "currency": "USD", "buying_power": float or None}

optional, shown when the file has them (the desk falls back to Yahoo through ysym otherwise)
login_url(cfg)           -> daily login: where the reader logs in
exchange_token(cfg, tok) -> daily login: turn what the redirect carried into today's token
futures(client)          -> open futures and options: [{"underlying", "contract", "expiry",
                            "side", "qty", "avg", "ltp", "notional", "mtm", "mtm_pct"}]
quote(client, code, exch)-> a live quote for the home watch grid and the home ticker page,
                            with bid/offer and their sizes when the broker gives a book
history(client, code, exch, years) -> daily candles newest first [{"date","price","o","h","l","v"}]
intraday(client, code, exch)       -> {"1D": [...], "5D": [...]} minute candles, same shape
futures_quote(client, code, expiry)-> bid, ask and open interest on one futures contract
sparks(client, futures)  -> {underlying: [closes]} three days of intraday closes per open future
tape(client)             -> [{"code","expiry","spot","pcr","flow_pcr","support","resistance",
                            "exp_move_pct","skew"}] the index options tape on Desk · Home
stream(client, load_names, sink, is_open) -> start live ticks for Watch · Home; sink(code, quote)
stream_healthy()         -> True while ticks arrive
resolve(code)            -> {"symbol", "exch", "name", "ysym", "meta"} for a broker code whose
                            exchange symbol differs from it (a symbol master)
search(q)                -> [{"code","name","exch"}] search-as-you-type over that master
extra_accounts(client, live_names) -> {name: block} other accounts at the same broker
commodities_local(client, cards)   -> attach local price lines to the Commodities cards
```

The market side (session hours, the index Risk measures against, the currency, the results calendar, the filings) is not the broker's job: `META["region"]` names a file in `markets/`, and that file supplies it for every broker in that market.

A row:

```
{"code": "AAPL", "name": "", "exch": "NASDAQ", "qty": 10.0, "avg": 172.4,
 "ltp": 189.1 or None, "value": None, "pnl": None, "pnl_pct": None, "day_pct": None,
 "currency": "USD", "ysym": "AAPL"}
```

Leave `ltp` as None when the broker gives no price: the desk marks the line from Yahoo through `ysym`, and `derive()` in `__init__.py` fills value, profit and profit percent from what is there. `ysym` is Yahoo Finance's symbol for the same share (AAPL, RELIANCE.NS, RR.L, 0700.HK).

Keep the file to the broker's own documented endpoints, catch its refusals and turn them into one plain sentence, and never write a key anywhere but the environment the desk hands you.
