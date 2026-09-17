"""ICICI Direct, through its Breeze API (India). App key and secret from
api.icicidirect.com (free for its clients) and a login every trading day: the
broker's login page redirects with apisession= in the address, and that value
is the day's token.

Beyond holdings and cash this broker hands out live ticks, open futures and
options, margin, index option chains, intraday candles and a symbol master, so
this file also carries the optional hooks the desk shows when a broker has
them: quote, history, intraday, futures_quote, sparks, tape, stream, resolve,
search, extra_accounts and commodities_local. The reads themselves live in
collect.py, stream_in.py, fno.py, pricing.py, secmaster.py and local_in.py;
this file is the door the broker layer opens them through. Nothing here
places an order."""

import json
import os
import threading
import time
from datetime import datetime, timedelta

from brokers import derive

META = {
    "label": "ICICI Direct (Breeze)",
    "where": "India",
    "region": "in",
    "daily_login": True,
    "docs": "https://api.icicidirect.com/apiuser/home",
    "how": "api.icicidirect.com: register an app once (free for ICICI Direct clients), set its redirect address to this desk's Settings address, and copy the key and secret. Then log in once each trading day from this screen.",
    "fields": [
        {"env": "BREEZE_API_KEY", "label": "App key", "secret": True},
        {"env": "BREEZE_API_SECRET", "label": "App secret", "secret": True},
    ],
    "token_hint": "After the login the page jumps to a localhost address with apisession= in it; paste that value, or the whole address.",
    "token_param": "apisession",
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAPE_PATH = os.path.join(ROOT, "data", "fno_watchlist.json")


def _num(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, "", "NA"):
            return d[k]
    return None


# ---- the contract: connect, label, equity, funds, futures --------------------
def login_url(cfg):
    from urllib.parse import quote
    return "https://api.icicidirect.com/apiuser/login?api_key=" + quote(cfg["BREEZE_API_KEY"], safe="")


def exchange_token(cfg, token):
    return token   # the apisession value is the day's token as it is


def connect(cfg, token=None):
    """A session from the keys the reader saved and today's apisession value, as they are.
    None when the broker rejects the token; the broker's own words when it says why."""
    if not token:
        return None
    from breeze_connect import BreezeConnect
    from . import BrokerError
    client = BreezeConnect(api_key=cfg["BREEZE_API_KEY"])
    try:
        client.generate_session(api_secret=cfg["BREEZE_API_SECRET"], session_token=token)
    except Exception as exc:  # noqa: BLE001
        why = str(exc).strip()
        if not why or "session" in why.lower() or "token" in why.lower():
            return None      # the login is stale or mistyped: the page says so in plain words
        raise BrokerError("ICICI Direct did not accept the keys: " + why[:160]) from exc
    return client


def label(client):
    try:
        f = client.get_funds().get("Success") or {}
        acct = str(f.get("bank_account") or "")
        if len(acct) >= 4:
            return f"A/C ··{acct[-4:]}"
    except Exception:  # noqa: BLE001
        pass
    return "account"


def _ysym(code, exch):
    r = resolve(code)
    return r.get("ysym", "") if r else ""


def equity(client):
    from collect import _equity
    rows = []
    for r in _equity(client):
        r["currency"] = "INR"
        r["ysym"] = _ysym(r.get("code"), r.get("exch"))
        rows.append(derive(r))
    return rows


def futures(client):
    from collect import _futures
    return _futures(client)


def funds(client):
    from collect import _funds
    f = _funds(client)
    f["currency"] = "INR"
    f["buying_power"] = f.get("fno_free")
    return f


# ---- the symbol master: this broker's short codes -> name, exchange, Yahoo ---
def resolve(code):
    """{"symbol": the NSE symbol, "exch", "name", "ysym", "meta"} for one of
    this broker's stock codes (RELIND -> RELIANCE, RELIANCE.NS); None when the
    master does not know the code."""
    import secmaster
    meta = secmaster.lookup(code)
    if not meta:
        return None
    exch = meta.get("exch") or "NSE"
    sym = meta.get("nse_symbol") or ""
    ysym = (sym + (".BO" if exch == "BSE" else ".NS")) if sym else ""
    return {"symbol": sym, "exch": exch, "name": (meta.get("company") or "").title(),
            "ysym": ysym, "meta": meta}


def code_of(symbol, exch=None):
    """This broker's code for an exchange symbol (HDFCBANK -> HDFBAN), so a name
    added by company name is quoted by the broker too. None when unknown."""
    import secmaster
    return secmaster.code_of(symbol, exch)


def search(q):
    """Search-as-you-type over the broker's own master: code, exchange symbol
    or company name."""
    import secmaster
    q = (q or "").strip().upper()
    if not q:
        return []
    db = secmaster.load()
    matches = []
    for code, meta in db.items():
        co = (meta.get("company") or "").upper()
        nse = (meta.get("nse_symbol") or "").upper()
        if code.startswith(q) or nse.startswith(q):
            matches.append((0, code, meta))
        elif q in co:
            matches.append((1, code, meta))
    matches.sort(key=lambda m: (m[0], m[1]))
    out = []
    for _, code, meta in matches[:8]:
        nse = meta.get("nse_symbol")
        out.append({"code": code, "name": (meta.get("company") or "").title(),
                    "exch": (meta.get("exch") or "") + (f" · {nse}" if nse else "")})
    return out


# ---- quotes and candles -------------------------------------------------------
def quote(client, code, exch="NSE"):
    """One cash quote in the watch-grid shape, with the order book. None if
    nothing came back."""
    try:
        r = client.get_quotes(stock_code=code, exchange_code=exch, product_type="cash")
    except Exception:  # noqa: BLE001
        return None
    rows = (r.get("Success") if isinstance(r, dict) else None) or []
    if not rows:
        return None
    q = rows[0]
    ltp = _num(_first(q, ["ltp", "last_traded_price"]))
    prev = _num(_first(q, ["previous_close", "prev_close"]))
    if ltp is None or ltp <= 0:
        return None
    # day % computed here: the feed's own percent field loses the sign
    day = (ltp - prev) / prev * 100 if prev else _num(_first(q, ["ltp_percent_change"]))
    return {
        "code": code, "exch": exch, "ltp": ltp, "prev": prev, "day_pct": day,
        "bid": _num(_first(q, ["best_bid_price"])),
        "bid_qty": _num(_first(q, ["best_bid_quantity"])),
        "offer": _num(_first(q, ["best_offer_price"])),
        "offer_qty": _num(_first(q, ["best_offer_quantity"])),
        "open": _num(_first(q, ["open"])), "high": _num(_first(q, ["high"])),
        "low": _num(_first(q, ["low"])),
        "ttq": _num(_first(q, ["total_quantity_traded", "volume"])),
        "ts": datetime.now().strftime("%H:%M:%S"),
    }


def history(client, code, exch="NSE", years=8):
    """Daily candles, newest first, pulled in three-year chunks (the API caps
    ~1000 rows per call). The desk caches the result per day."""
    out, now = [], datetime.now()
    for y0 in range(now.year - years, now.year + 1, 3):
        frm = f"{y0}-01-01T09:00:00.000Z"
        to = min(datetime(y0 + 3, 1, 1), now).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        try:
            r = client.get_historical_data_v2(
                interval="1day", from_date=frm, to_date=to,
                stock_code=code, exchange_code=exch, product_type="cash")
            rows = r.get("Success") or []
        except Exception:  # noqa: BLE001
            rows = []
        for c in rows:
            p = _num(c.get("close"))
            if p:
                out.append({"date": str(c.get("datetime"))[:10], "price": p,
                            "o": _num(c.get("open")), "h": _num(c.get("high")),
                            "l": _num(c.get("low")), "v": _num(c.get("volume"))})
        time.sleep(0.15)
    seen, dedup = set(), []
    for row in out:
        if row["date"] not in seen:
            seen.add(row["date"])
            dedup.append(row)
    return sorted(dedup, key=lambda r: r["date"], reverse=True)


def intraday(client, code, exch="NSE"):
    """{"1D": 1-minute candles of the latest session, "5D": 5-minute over five}."""
    now = datetime.now()
    out = {}
    for key, interval, back in (("1D", "1minute", 6), ("5D", "5minute", 12)):
        try:
            r = client.get_historical_data_v2(
                interval=interval,
                from_date=(now - timedelta(days=back)).strftime("%Y-%m-%dT09:00:00.000Z"),
                to_date=now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                stock_code=code, exchange_code=exch, product_type="cash")
            rows = r.get("Success") or []
        except Exception:  # noqa: BLE001
            rows = []
        pts = [{"date": str(c.get("datetime"))[:16], "price": _num(c.get("close")),
                "o": _num(c.get("open")), "h": _num(c.get("high")),
                "l": _num(c.get("low")), "v": _num(c.get("volume"))}
               for c in rows if _num(c.get("close"))]
        dates = sorted({p["date"][:10] for p in pts})
        keep = dates[-1:] if key == "1D" else dates[-5:]
        out[key] = [p for p in pts if p["date"][:10] in keep]
        time.sleep(0.2)
    return out


def futures_quote(client, code, expiry_human):
    """Bid, ask and open interest on one futures contract. The position carries
    27-Oct-2026; the API wants an ISO date, so both are tried."""
    try:
        iso = datetime.strptime(expiry_human, "%d-%b-%Y").strftime("%Y-%m-%dT06:00:00.000Z")
    except (ValueError, TypeError):
        return None
    for exp in (iso, expiry_human):
        try:
            r = client.get_quotes(stock_code=code, exchange_code="NFO",
                                  product_type="futures", expiry_date=exp,
                                  right="others", strike_price="0")
            rows = (r.get("Success") if isinstance(r, dict) else None) or []
        except Exception:  # noqa: BLE001
            rows = []
        if rows:
            q = rows[0]
            return {
                "expiry": expiry_human,
                "ltp": _num(q.get("ltp")),
                "bid": _num(q.get("best_bid_price")), "bid_qty": _num(q.get("best_bid_quantity")),
                "offer": _num(q.get("best_offer_price")), "offer_qty": _num(q.get("best_offer_quantity")),
                "oi": _num(q.get("open_interest")),
                "ttq": _num(q.get("total_quantity_traded")),
                "prev": _num(q.get("previous_close")),
            }
        time.sleep(0.3)
    return None


def sparks(client, futures_rows):
    """Three days of 5-minute closes for the underlying of each open future,
    drawn as the sparkline in the futures table. At most six names."""
    from pricing import _pull_candles
    out = {}
    seen = []
    for f in futures_rows or []:
        u = f.get("underlying")
        if u and u not in seen:
            seen.append(u)
    for code in seen[:6]:
        candles = _pull_candles(client, code, "NSE", days=3)
        closes = [c.get("close") for c in candles if c.get("close") is not None]
        if closes:
            out[code] = closes[-120:]
    return out


# ---- the index options tape ----------------------------------------------------
def _tape_names():
    try:
        import lists as desk_lists            # the reader's own list, starters from the file below
        rows = desk_lists.effective("fno")
    except Exception:  # noqa: BLE001
        try:
            with open(TAPE_PATH) as fh:
                rows = json.load(fh).get("names", [])
        except (OSError, ValueError):
            return []
    return [(r.get("stock_code"), r.get("exchange_code") or "NFO") for r in rows if r.get("stock_code")]


def tape(client):
    """Put/call, walls, expected move and skew for each index in
    data/fno_watchlist.json."""
    from fno import analyze, find_chain
    out = []
    for code, exch in _tape_names():
        calls, puts, expiry = find_chain(client, code, exch)
        if not calls:
            out.append({"code": code, "error": "no chain"})
            continue
        m = analyze(calls, puts)
        out.append({
            "code": code, "expiry": expiry, "spot": m["spot"],
            "pcr": m["pcr_oi"], "flow_pcr": m["flow_pcr"],
            "support": m["support"][0] if m["support"] else None,
            "resistance": m["resistance"][0] if m["resistance"] else None,
            "exp_move_pct": m["exp_move_pct"], "skew": m["skew"],
        })
    return out


# ---- live ticks for Watch · Home ------------------------------------------------
_stream = {"on": False}


def stream(client, load_names, sink, is_open):
    """Start the websocket once; ticks land in sink(code, quote) during the
    session and the socket rests outside it."""
    if _stream["on"]:
        return
    _stream["on"] = True
    import stream_in
    threading.Thread(target=stream_in.manager,
                     args=(client, load_names, sink, is_open), daemon=True).start()


def stream_healthy():
    import stream_in
    return stream_in.healthy()


# ---- several accounts at this broker -------------------------------------------
def extra_accounts(client, live_names):
    """This broker supports more than one account (ACCOUNTS in
    breeze_session.py). For each one with no session today, the last saved
    book with its marks re-priced through the live session; funds and margin
    stay as the broker last reported them."""
    from breeze_session import ACCOUNTS
    from collect import load_last_snapshot_block, refresh_marks
    out = {}
    for name in ACCOUNTS:
        if name in live_names:
            continue
        block, as_of = load_last_snapshot_block(name)
        if not block:
            continue
        try:
            refresh_marks(block, client)
        except Exception:  # noqa: BLE001
            pass
        block["stale_funds"] = True
        block["broker_as_of"] = as_of
        out[name] = block
    return out


# ---- local reads for the Commodities screen -------------------------------------
def commodities_local(client, cards):
    """MCX front-month futures through this broker's history endpoint and the
    Rubber Board of India's daily sheet, attached to the matching cards."""
    import local_in
    try:
        rb = local_in.rubber_board()
    except Exception:  # noqa: BLE001
        rb = None
    try:
        mcx = local_in.mcx_quotes(client)
    except Exception:  # noqa: BLE001
        mcx = {}
    for c in cards:
        loc = []
        short = local_in.MCX_MAP.get(c["id"])
        if short and short in mcx:
            m = mcx[short]
            loc.append({"kind": "exchange", "tag": "MCX", "label": f"MCX {m['name']} {m['expiry']}",
                        "note": "front-month MCX future through the broker feed",
                        "level": m["level"], "unit": m["unit"], "day_pct": m["day_pct"],
                        "oi": m["oi"], "ts": m["ts"], "hist": m["hist"]})
        if c["id"] == "rubber" and rb and rb.get("grades", {}).get("RSS4"):
            g = rb["grades"]["RSS4"]
            loc.append({"kind": "local", "tag": "INDIA", "label": f"Kottayam RSS4 · Rubber Board {rb.get('date', '')}",
                        "short": "Kottayam RSS4", "note": "the domestic grade Indian tyre makers buy",
                        "detail": "India domestic",
                        "level": g["inr_per_kg"], "unit": "₹/kg", "usc_per_kg": g["usc_per_kg"],
                        "stale": rb.get("stale", False), "ts": rb.get("date")})
        if loc:
            c["local"] = loc
    return bool(mcx)
