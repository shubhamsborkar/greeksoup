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

optional
futures(client)          -> open futures and options (see collect.py for the shape)
quote(client, code, exch)-> a quote for the home watch grid (else the desk uses Yahoo)
login_url(cfg)           -> daily login: where the reader logs in
exchange_token(cfg, tok) -> daily login: turn what the redirect carried into today's token
```

A row:

```
{"code": "AAPL", "name": "", "exch": "NASDAQ", "qty": 10.0, "avg": 172.4,
 "ltp": 189.1 or None, "value": None, "pnl": None, "pnl_pct": None, "day_pct": None,
 "currency": "USD", "ysym": "AAPL"}
```

Leave `ltp` as None when the broker gives no price: the desk marks the line from Yahoo through `ysym`, and `derive()` in `__init__.py` fills value, profit and profit percent from what is there. `ysym` is Yahoo Finance's symbol for the same share (AAPL, RELIANCE.NS, RR.L, 0700.HK).

Keep the file to the broker's own documented endpoints, catch its refusals and turn them into one plain sentence, and never write a key anywhere but the environment the desk hands you.
