"""Commodity board: level, changes over five windows, distance from the old
peaks, and the universal commodity -> industry exposure map from
commodities.json. Three keyless sources, each used for what it is good at:

  Yahoo chart API   daily history + live level for exchange-traded contracts
  Trading Economics the summary sentence only (level, day, month, year change)
                    for what has no Yahoo contract (rubber, zinc, urea ...)
  FRED (IMF/WB)     monthly history, two to three months behind, for the long
                    chart and the vs-peak read when Yahoo has nothing

Read-only reference; nothing here trades. Scraped pages break silently, so
every scraped value is date-stamped and the last good value persists on disk.
"""
import json
import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
def _find(name):
    """The project root first, then data/ (the public desk keeps its editable
    JSON in data/; the private one keeps it beside the code)."""
    for d in (HERE, os.path.join(HERE, "data")):
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    return os.path.join(HERE, name)


CFG_PATH = _find("commodities.json")
CACHE_DIR = os.path.join(HERE, "cache", "commods")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HIST_TTL = 12 * 3600      # full daily/monthly history refetch
TE_TTL = 45 * 60          # Trading Economics sentence
_yahoo_gate = threading.Semaphore(2)   # keyless API: never more than two in flight


def load_config():
    with open(CFG_PATH) as fh:
        return json.load(fh)


def load_exposure():
    """Every exposure_<market>.json beside this file: the per-market names
    layer. Missing files are fine (the replica ships none)."""
    import glob
    names = []
    for path in sorted(set(glob.glob(os.path.join(HERE, "exposure_*.json")) +
                           glob.glob(os.path.join(HERE, "data", "exposure_*.json")))):
        try:
            with open(path) as fh:
                blob = json.load(fh)
        except (OSError, ValueError):
            continue
        market = blob.get("market") or os.path.basename(path)[9:-5]
        for n in blob.get("names", []):
            if n.get("code"):
                n = dict(n)
                n["region"] = market
                names.append(n)
    return names


_SELLER_WORDS = ("miner", "smelter", "producer", "estate", "plantation", "grower",
                 "exporter", "shipowner", "crusher", "oil & gas", "gas producers")


def attach_names(card, names):
    """Names whose `commodities` list carries this card's id. The side comes
    from where the name's industry sits on the card (cost or revenue); a name
    can force it with its own `side`."""
    cost = {s.lower() for s in card.get("cost", [])}
    rev = {s.lower() for s in card.get("revenue", [])}
    out = []
    for n in names:
        if card["id"] not in (n.get("commodities") or []):
            continue
        ind = (n.get("industry") or "").lower()
        # per-commodity override first (an integrated steel maker is squeezed
        # by coking coal but helped by iron ore), then the industry's place on
        # this card, then the name's own default
        side = ((n.get("sides") or {}).get(card["id"])
                or ("cost" if ind in cost else "revenue" if ind in rev else None)
                or n.get("side")
                # an industry not listed on this card: producers of things sit
                # on the revenue side, everyone else buys
                or ("revenue" if any(w in ind for w in _SELLER_WORDS) else "cost"))
        out.append({k: n.get(k) for k in ("code", "region", "label", "industry", "intensity",
                                          "intensity_source", "lag", "pricing_power", "note")}
                   | {"side": side})
    return out


# ---- tiny disk cache --------------------------------------------------------
def _cpath(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, re.sub(r"[^A-Za-z0-9_.-]", "_", name) + ".json")


def _cget(name, ttl):
    try:
        with open(_cpath(name)) as fh:
            c = json.load(fh)
        if time.time() - c.get("at", 0) < ttl:
            return c.get("data")
    except (OSError, ValueError):
        pass
    return None


def _cget_any(name):
    """Last good value regardless of age (the stale-but-dated fallback)."""
    try:
        with open(_cpath(name)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _cput(name, data):
    try:
        with open(_cpath(name), "w") as fh:
            json.dump({"at": time.time(), "data": data}, fh)
    except OSError:
        pass


# ---- Yahoo -------------------------------------------------------------------
def _yahoo_chart(symbol, rng, interval="1d"):
    # the bare "Mozilla/5.0" agent is the one Yahoo serves keyless without a
    # 429; a full browser string gets throttled. One polite retry on 429.
    with _yahoo_gate:
        for attempt in (1, 2):
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                             params={"range": rng, "interval": interval},
                             headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            if r.status_code != 429:
                break
            time.sleep(4 * attempt)
        time.sleep(0.8)
    if r.status_code != 200:
        return None, {}
    res = r.json().get("chart", {}).get("result")
    if not res:
        return None, {}
    res = res[0]
    ts = res.get("timestamp") or []
    closes = (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    pts = []
    for t, c in zip(ts, closes):
        if c is not None:
            pts.append((datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"), float(c)))
    return pts, res.get("meta", {})


def yahoo_series(symbol):
    """Full daily history (cached 12h) refreshed with the last month so the
    tail is live, plus the current level from the chart meta."""
    key = f"yh_{symbol}"
    hist = _cget(key, HIST_TTL)
    if hist is None:
        try:
            # "10y" explicitly: "max" on futures comes back thinner than 10y
            pts, _ = _yahoo_chart(symbol, "10y")
        except Exception:  # noqa: BLE001
            pts = None
        if pts:
            hist = pts
            _cput(key, hist)
        else:
            old = _cget_any(key)
            hist = (old or {}).get("data") or []
    try:
        recent, meta = _yahoo_chart(symbol, "1mo")
    except Exception:  # noqa: BLE001
        recent, meta = [], {}
    series = [tuple(p) for p in hist]
    if recent:
        cut = recent[0][0]
        series = [p for p in series if p[0] < cut] + recent
    live = meta.get("regularMarketPrice")
    live_t = meta.get("regularMarketTime")
    live_date = (datetime.fromtimestamp(live_t, timezone.utc).strftime("%Y-%m-%d")
                 if live_t else None)
    if live is not None and series:
        if live_date and live_date > series[-1][0]:
            series.append((live_date, float(live)))
        elif live_date == series[-1][0]:
            series[-1] = (live_date, float(live))
    return series, (float(live) if live is not None else None), live_date, meta.get("currency")


# ---- FRED (monthly IMF / World Bank series) ----------------------------------
def fred_series(series_id):
    key = f"fred_{series_id}"
    data = _cget(key, HIST_TTL)
    if data is not None:
        return [tuple(p) for p in data]
    out = []
    try:
        # FRED's CDN stalls python-requests' TLS fingerprint; curl is fine.
        r = subprocess.run(["curl", "-s", "-m", "25",
                            f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"],
                           capture_output=True, text=True, timeout=30)
        for ln in r.stdout.strip().splitlines()[1:]:
            d, _, v = ln.partition(",")
            v = v.strip()
            if v and v != ".":
                try:
                    out.append((d, float(v)))
                except ValueError:
                    pass
    except Exception:  # noqa: BLE001
        out = []
    if out:
        _cput(key, out)
        return out
    old = _cget_any(key)
    return [tuple(p) for p in ((old or {}).get("data") or [])]


# ---- Trading Economics summary sentence --------------------------------------
_TE_LEVEL = re.compile(
    r"(?:rose|fell|increased|decreased|climbed|dropped|jumped|slipped|surged|"
    r"plunged|edged\s+(?:up|down)|was\s+unchanged|remained\s+(?:unchanged|flat)|"
    r"held\s+steady|hovered)\s+(?:to|at|around|near)?\s*([\d,]+(?:\.\d+)?)\s*"
    r"([A-Za-z€$£¥][^<\n,]{0,28}?)\s+on\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})")
_TE_DAY = re.compile(r"(up|down)\s+([\d.]+)%\s+from\s+the\s+previous\s+day")
_TE_MONTH = re.compile(r"past\s+month[^.]*?(risen|fallen|increased|decreased|gained|lost)\s+([\d.]+)%")
_TE_YEAR_A = re.compile(r"is\s+(up|down)\s+([\d.]+)%\s+compared\s+to\s+the\s+same\s+time\s+last\s+year")
_TE_YEAR_B = re.compile(r"([\d.]+)%\s+(higher|lower)\s+than\s+a\s+year\s+ago")


def te_current(slug):
    """level + day/month/year change from the page's summary sentence. Cached
    45 minutes; a failed fetch returns the last good read flagged stale."""
    key = f"te_{slug}"
    data = _cget(key, TE_TTL)
    if data is not None:
        return data
    html = ""
    try:
        r = subprocess.run(["curl", "-s", "-m", "25", "-A", UA,
                            f"https://tradingeconomics.com/commodity/{slug}"],
                           capture_output=True, text=True, timeout=30)
        html = r.stdout.replace("&#39;", "'").replace("&amp;", "&")
    except Exception:  # noqa: BLE001
        pass
    m = _TE_LEVEL.search(html)
    if m:
        try:
            level = float(m.group(1).replace(",", ""))
            date = datetime.strptime(m.group(3), "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            level, date = None, None
        if level is not None:
            unit = re.sub(r"\s+", " ", m.group(2)).strip()
            sign = lambda w: 1 if w in ("up", "risen", "increased", "gained", "higher") else -1  # noqa: E731
            d = _TE_DAY.search(html)
            mo = _TE_MONTH.search(html)
            ya = _TE_YEAR_A.search(html)
            yb = _TE_YEAR_B.search(html)
            out = {"level": level, "unit": unit, "date": date,
                   "d1": sign(d.group(1)) * float(d.group(2)) if d else None,
                   "m1": sign(mo.group(1)) * float(mo.group(2)) if mo else None,
                   "y1": (sign(ya.group(1)) * float(ya.group(2)) if ya else
                          (sign(yb.group(2)) * float(yb.group(1)) if yb else None)),
                   "stale": False}
            _cput(key, out)
            return out
    old = _cget_any(key)
    if old and old.get("data"):
        stale = dict(old["data"])
        stale["stale"] = True
        stale["fetched"] = datetime.fromtimestamp(old["at"]).strftime("%Y-%m-%d %H:%M")
        return stale
    return None


# ---- statistics ---------------------------------------------------------------
def _value_at(series, target):
    """Last point on or before the target date (series sorted ascending)."""
    best = None
    for d, v in series:
        if d <= target:
            best = v
        else:
            break
    return best


def _pct(a, b):
    return ((a / b) - 1) * 100 if (a is not None and b) else None


def _peak(series):
    if not series:
        return None
    d, v = max(series, key=lambda p: p[1])
    return {"v": v, "date": d}


def _trough(series):
    if not series:
        return None
    d, v = min(series, key=lambda p: p[1])
    return {"v": v, "date": d}


def _downsample(series):
    """Daily for the last two years, weekly before that: keeps the modal chart
    honest and the payload small."""
    if len(series) < 800:
        return series
    cut = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    old = [p for p in series if p[0] < cut]
    new = [p for p in series if p[0] >= cut]
    return old[::5] + new


def _spark(series, days=365, n=70):
    cut = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    pts = [v for d, v in series if d >= cut] or [v for _, v in series[-n:]]
    if len(pts) > n:
        step = len(pts) / n
        pts = [pts[int(i * step)] for i in range(n)] + [pts[-1]]
    return pts


def is_daily(series):
    """Daily if the last few points are days apart, monthly if weeks apart."""
    if len(series) < 6:
        return True
    a = datetime.strptime(series[-6][0], "%Y-%m-%d")
    b = datetime.strptime(series[-1][0], "%Y-%m-%d")
    return (b - a).days <= 12


def stats(series, daily=None):
    """Windows and peaks from a sorted (date, value) series whose last point is
    the current level."""
    if not series:
        return {}
    if daily is None:
        daily = is_daily(series)
    last_d, last = series[-1]
    now = datetime.strptime(last_d, "%Y-%m-%d")
    win = {}
    if daily:
        win["1d"] = _pct(last, series[-2][1]) if len(series) > 1 else None
        win["1w"] = _pct(last, _value_at(series, (now - timedelta(days=7)).strftime("%Y-%m-%d")))
    win["1m"] = _pct(last, _value_at(series, (now - timedelta(days=30)).strftime("%Y-%m-%d")))
    win["3m"] = _pct(last, _value_at(series, (now - timedelta(days=91)).strftime("%Y-%m-%d")))
    win["1y"] = _pct(last, _value_at(series, (now - timedelta(days=365)).strftime("%Y-%m-%d")))
    y1 = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    y5 = (now - timedelta(days=5 * 365)).strftime("%Y-%m-%d")
    s1 = [p for p in series if p[0] >= y1]
    s5 = [p for p in series if p[0] >= y5]
    hi52, lo52 = _peak(s1), _trough(s1)
    hi5, hiall = _peak(s5), _peak(series)
    return {
        "chg": win, "hi52": hi52, "lo52": lo52, "hi5y": hi5, "hiall": hiall,
        "from_5y_high": _pct(last, hi5["v"]) if hi5 else None,
        "from_all_high": _pct(last, hiall["v"]) if hiall else None,
        "years": round((now - datetime.strptime(series[0][0], "%Y-%m-%d")).days / 365.25, 1),
    }


# ---- one card -----------------------------------------------------------------
def _card(c):
    src = c.get("sources", {})
    card = {"id": c["id"], "label": c["label"], "group": c["group"],
            "unit": c.get("unit", ""), "cost": c.get("cost", []),
            "revenue": c.get("revenue", []), "note": c.get("note", ""),
            "value": None, "date": None, "chg": {}, "stale": False}
    if src.get("yahoo"):
        series, live, live_date, ccy = yahoo_series(src["yahoo"])
        if series:
            st = stats(series, daily=True)
            card.update(st)
            card["value"], card["date"] = series[-1][1], series[-1][0]
            card["spark"] = _spark(series)
            card["full"] = _downsample(series)
            card["hist_kind"] = "daily"
            card["hist_through"] = series[-1][0]
            card["src_live"] = f"Yahoo {src['yahoo']}"
            card["src_hist"] = f"Yahoo {src['yahoo']}"
            if live is None:
                card["stale"] = True
            return card
    if src.get("yahoo"):
        card["stale"] = True     # Yahoo answered nothing; whatever follows is a fallback
    te = te_current(src["te"]) if src.get("te") else None
    fred = fred_series(src["fred"]) if src.get("fred") else []
    if fred:
        daily = is_daily(fred)
        st = stats(fred, daily=daily)
        card.update(st)
        card["spark"] = _spark(fred) if daily else _spark(fred, days=3 * 365, n=48)
        card["full"] = _downsample(fred) if daily else fred
        card["hist_kind"] = "daily" if daily else "monthly"
        card["hist_through"] = fred[-1][0]
        card["src_hist"] = f"FRED {src['fred']}" + ("" if daily else " (IMF monthly)")
        card["value"], card["date"] = fred[-1][1], fred[-1][0]
        card["unit"] = c.get("fred_unit") or card["unit"]
        card["peak_basis"] = "daily" if daily else "monthly"
        # the peak is in FRED's unit, which may differ from the live level's
        card["peak_unit"] = c.get("fred_unit") or ""
    if te:
        # the sentence is the live read; FRED's level is an older benchmark on
        # its own unit, so the level and the short windows come from TE only
        card["value"], card["date"] = te["level"], te["date"]
        if te.get("unit"):
            card["unit"] = te["unit"]
        card["chg"] = {"1d": te.get("d1"), "1m": te.get("m1"), "1y": te.get("y1")}
        card["src_live"] = f"Trading Economics ({te['date']})"
        card["stale"] = bool(te.get("stale"))
        if te.get("stale"):
            card["src_live"] += f" · last good {te.get('fetched')}"
        if fred:
            card["fred_level"] = fred[-1][1]
            card["fred_date"] = fred[-1][0]
            card["fred_unit"] = c.get("fred_unit") or ""
    if card["value"] is None:
        card["stale"] = True
    return card


def cross_link(cards):
    """A name can sit on several cards, sometimes on opposite sides (an
    integrated steel maker: squeezed by coking coal, helped by iron ore).
    Give every name entry the list of its OTHER cards with side and the
    one-month move, and a net score = sum of signed one-month moves across
    all its cards (cost side counts against, revenue side for). Unweighted:
    it ranks who is under the most commodity pressure this month, it does
    not size it."""
    by_name = {}
    for c in cards:
        for n in c.get("names", []):
            by_name.setdefault(f"{n['region']}:{n['code']}", []).append(
                {"id": c["id"], "label": c["label"], "side": n["side"],
                 "chg": (c.get("chg") or {}).get("1m"),
                 "chg1d": (c.get("chg") or {}).get("1d")})
    for c in cards:
        for n in c.get("names", []):
            parts = by_name.get(f"{n['region']}:{n['code']}", [])
            n["also"] = [p for p in parts if p["id"] != c["id"]]
            n["net"] = round(sum((p["chg"] or 0) * (1 if p["side"] == "revenue" else -1)
                                 for p in parts), 1) if any(p["chg"] is not None for p in parts) else None
    return by_name


def pressure(cards, by_name, n=10):
    """The names under the most commodity pressure this month, both ways."""
    seen, rows = set(), []
    for c in cards:
        for nm in c.get("names", []):
            key = f"{nm['region']}:{nm['code']}"
            if key in seen or nm.get("net") is None:
                continue
            seen.add(key)
            parts = sorted(by_name.get(key, []), key=lambda p: -abs(p["chg"] or 0))
            rows.append({"code": nm["code"], "region": nm["region"], "label": nm["label"],
                         "net": nm["net"], "ltp": nm.get("ltp"), "day_pct": nm.get("day_pct"),
                         "ccy": nm.get("ccy"),
                         "parts": [{"id": p["id"], "label": p["label"], "side": p["side"],
                                    "chg": p["chg"]} for p in parts if p["chg"] is not None][:5]})
    rows.sort(key=lambda r: r["net"])
    return {"squeezed": [r for r in rows if r["net"] < 0][:n],
            "helped": [r for r in reversed(rows) if r["net"] > 0][:n]}


def build(items=None):
    """The board. `items` is the reader's own list when the desk passes one; the shipped
    commodities.json otherwise (the scripts and tests that call this alone)."""
    cfg = load_config()
    items = items if items is not None else cfg.get("commodities", [])
    with ThreadPoolExecutor(max_workers=5) as ex:
        cards = list(ex.map(_card, items))
    order = {g: i for i, g in enumerate(cfg.get("groups", []))}
    for c in cards:                                  # a group the reader named goes after the shipped ones
        order.setdefault(c["group"], len(order))
    cards.sort(key=lambda c: (order.get(c["group"], 99),))
    names = load_exposure()
    for c in cards:
        c["names"] = attach_names(c, names)
    live = [c for c in cards if c.get("value") is not None]

    def top(key, n=8, daily_only=False):
        pool = [c for c in live if c.get("chg", {}).get(key) is not None]
        if daily_only:
            pool = [c for c in pool if c.get("hist_kind") == "daily" or key == "1d"]
        pool.sort(key=lambda c: -abs(c["chg"][key]))
        return [{"id": c["id"], "label": c["label"], "pct": round(c["chg"][key], 2),
                 "value": c["value"], "unit": c["unit"]} for c in pool[:n]]

    near_peak = sorted(
        [{"id": c["id"], "label": c["label"], "from": round(c["from_5y_high"], 2),
          "peak": c["hi5y"], "basis": c.get("peak_basis", "daily"),
          "peak_unit": c.get("peak_unit", "")}
         for c in live if c.get("from_5y_high") is not None and c["from_5y_high"] >= -5],
        key=lambda r: -r["from"])
    by_name = cross_link(cards)
    return {"cards": cards,
            "movers": {"1d": top("1d"), "1w": top("1w"), "1m": top("1m"), "1y": top("1y")},
            "near_peak": near_peak,
            "pressure": pressure(cards, by_name),
            "n_live": len(live), "n_total": len(cards),
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}


if __name__ == "__main__":
    t0 = time.time()
    d = build()
    print(f"{d['n_live']}/{d['n_total']} live in {time.time() - t0:.1f}s")
    for c in d["cards"]:
        ch = c.get("chg", {})
        f = lambda k: ("%+.1f%%" % ch[k]) if ch.get(k) is not None else "   -  "  # noqa: E731
        pk = c.get("from_5y_high")
        print(f"{c['label']:<24} {str(c.get('value')):>10} {c.get('unit',''):<12} "
              f"1d {f('1d')} 1m {f('1m')} 1y {f('1y')}  vs5yHi "
              f"{('%+.1f%%' % pk) if pk is not None else '  -  '}  "
              f"{'STALE ' if c.get('stale') else ''}{c.get('src_live','')}")
    print("\nMOVERS 1m:", [(m['label'], m['pct']) for m in d['movers']['1m'][:6]])
    print("NEAR 5Y HIGH:", [(r['label'], r['from']) for r in d['near_peak'][:8]])
