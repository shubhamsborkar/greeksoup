"""India-local commodity reads that sit beside the global benchmark on the
Commodities board. Two plugins, both optional, both read-only:

  rubber_board()   the Rubber Board of India's daily domestic price sheet
                   (Kottayam RSS4 and friends, INR per 100 kg + a USD column)
  mcx_quotes()     MCX front-month futures through Breeze. The quote endpoint
                   rejects MCX (500 "object reference"), but historical v2 does
                   not: daily candles carry close + open interest, and the last
                   1-minute candle is the live-enough level (MCX runs to 23:30).

The MCX contract master is a separate file from the one secmaster.py caches:
ICICI's MotherAppMaster zip carries MCXScripMaster.txt, the NewSecurityMaster
zip does not.
"""
import csv
import io
import json
import os
import re
import subprocess
import time
import zipfile
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache", "commods")
MCX_ZIP = os.path.join(HERE, "cache", "mcx_master.zip")
MCX_URL = "https://directlink.icicidirect.com/MotherAppMaster/SecurityMaster.zip"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

# board commodity id -> MCX ShortName (the main contract, not the mini)
MCX_MAP = {
    "gold": "GOLD", "silver": "SILVER", "wti": "CRUDE", "natgas_us": "NATGAS",
    "copper": "COPPER", "zinc": "ZINC", "aluminium": "ALUMIN", "lead": "LEAD",
    "nickel": "NICKEL", "cotton": "COTTON", "steel_cn": "STEEL",
}
# board commodity id -> the benchmark mandi for the crop: the API's commodity name, the
# state, the market as the API spells it, the variety that is the reference grade there,
# and the words a reader sees. The choice of market is the trade's own: Indore for wheat
# and soybean (the Malwa belt), Davangere for maize, Raichur for kapas, Muzaffarnagar for
# gur. Rice is not here: mandi rows mix basmati and common grades under one name.
MANDI_MAP = {
    "wheat": {"commodity": "Wheat", "state": "Madhya Pradesh", "market": "Indore APMC", "variety": "Mill Quality",
              "short": "Indore wheat, mill quality", "detail": "India mandi", "note": "the milling grade flour and biscuit makers buy, Indore APMC"},
    "soybeans": {"commodity": "Soyabean", "state": "Madhya Pradesh", "market": "Indore APMC", "variety": "Soyabeen",
                 "short": "Indore soybean", "detail": "India mandi", "note": "the soybean crushers' reference market, Indore APMC"},
    "corn": {"commodity": "Maize", "state": "Karnataka", "market": "Davangere APMC", "variety": "Local",
             "short": "Davangere maize", "detail": "India mandi", "note": "the maize hub for feed and starch, Davangere APMC"},
    "cotton": {"commodity": "Cotton", "state": "Karnataka", "market": "Raichur APMC", "variety": "H4",
               "short": "Raichur kapas (seed cotton)", "detail": "India mandi", "note": "kapas, seed cotton before ginning, at Raichur APMC; lint trades ex-gin"},
    "sugar": {"commodity": "Gur(Jaggery)", "state": "Uttar Pradesh", "market": "Muzzafarnagar APMC", "variety": None,
              "short": "Muzaffarnagar gur (jaggery)", "detail": "India mandi", "note": "gur is the mandi-traded sugar proxy; sugar itself sells ex-mill on the mills' own contracts"},
}
MANDI_URL = "https://mandi-api.onrender.com/v1/prices"
MANDI_HIST_URL = "https://mandi-api.onrender.com/v1/prices/history"

MCX_UNIT = {"RS/10GRMS": "₹/10g", "RS/1KGS": "₹/kg", "RS/1BBL": "₹/bbl",
            "RS/1mmBtu": "₹/MMBtu", "RS/1BALES": "₹/bale", "RS/1MT": "₹/t"}


def _cpath(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, name + ".json")


def _cget(name, ttl):
    try:
        with open(_cpath(name)) as fh:
            c = json.load(fh)
        if time.time() - c.get("at", 0) < ttl:
            return c.get("data")
    except (OSError, ValueError):
        pass
    return None


def _cold(name):
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


# ---- Rubber Board of India ---------------------------------------------------
def rubber_board():
    """Kottayam RSS4 (the grade Indian tyre makers actually buy) from the
    board's public page. INR per 100 kg on the page -> INR/kg here, plus the
    board's own USD column as US cents per kg so it sits next to the global
    benchmark. Cached 6h; a failed fetch returns the last good sheet, stale."""
    data = _cget("rubber_board", 6 * 3600)
    if data:
        return data
    html = ""
    try:
        r = subprocess.run(["curl", "-s", "-m", "25", "-A", UA,
                            "https://rubberboard.gov.in/public"],
                           capture_output=True, text=True, timeout=30)
        html = r.stdout
    except Exception:  # noqa: BLE001
        pass
    txt = re.sub(r"<[^>]+>", "|", html).replace("&nbsp;", " ").replace("&#160;", " ")
    txt = re.sub(r"[|\s]+", " ", txt)
    # the sheet's own date is the last dd-mm-yyyy before the first RSS4 cell
    head = txt[:txt.find("RSS4")] if "RSS4" in txt else txt
    dates = re.findall(r"(\d{2}-\d{2}-\d{4})", head)
    m_date = re.match(r"(.*)", dates[-1]) if dates else None
    out = {"grades": {}}
    for grade in ("RSS4", "RSS5", "ISNR20"):
        m = re.search(grade + r"\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)", txt)
        if m:
            inr100 = float(m.group(1).replace(",", ""))
            usd100 = float(m.group(2).replace(",", ""))
            out["grades"][grade] = {"inr_per_kg": round(inr100 / 100, 2),
                                    "usc_per_kg": round(usd100, 2)}
    if out["grades"] and m_date:
        try:
            out["date"] = datetime.strptime(m_date.group(1), "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            out["date"] = m_date.group(1)
        out["market"] = "Kottayam"
        out["stale"] = False
        _cput("rubber_board", out)
        return out
    old = _cold("rubber_board")
    if old and old.get("data"):
        d = dict(old["data"])
        d["stale"] = True
        return d
    return None


# ---- MCX contract master -----------------------------------------------------
def _mandi_get(url, params):
    import requests
    r = requests.get(url, params=params, timeout=20, headers={"User-Agent": UA})
    if r.status_code != 200:
        return None
    j = r.json()
    return j.get("data") if isinstance(j, dict) and j.get("success") else None


def mandi_prices(fetch=None):
    """One local line per crop in MANDI_MAP, keyed by the board id: the benchmark
    market's latest modal price in rupees per quintal (the reference variety, within
    ten days), else the state's latest daily average across markets, marked as such;
    the day's change against the same market's previous row; the state-wide daily
    average as the history. Cached six hours; a failed fetch returns the last good
    sheet, stale. `fetch(url, params)` is injectable for the tests."""
    data = _cget("mandi_in", 6 * 3600)
    if data:
        return data
    get = fetch or _mandi_get
    out = {}
    for cid, m in MANDI_MAP.items():
        try:
            rows = get(MANDI_URL, {"state": m["state"], "commodity": m["commodity"]}) or []
            hist = get(MANDI_HIST_URL, {"state": m["state"], "commodity": m["commodity"]}) or []
        except Exception:  # noqa: BLE001
            continue
        rows = [r for r in rows if r.get("modal_price") and r.get("arrival_date")]
        if not rows:
            continue
        latest = max(r["arrival_date"] for r in rows)
        cutoff = (datetime.strptime(latest, "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d")
        mine = sorted((r for r in rows if r.get("market", "").strip() == m["market"]
                       and (m["variety"] is None or r.get("variety") == m["variety"]) and r["arrival_date"] >= cutoff),
                      key=lambda r: r["arrival_date"])
        series = [[h["arrival_date"], float(h["avg_modal_price"])] for h in hist if h.get("avg_modal_price")]
        if mine:
            level, ts, label = float(mine[-1]["modal_price"]), mine[-1]["arrival_date"], m["short"]
            prev = mine[-2]["modal_price"] if len(mine) > 1 else None
            state_avg = False
        else:
            day = [r for r in rows if r["arrival_date"] == latest]
            level = sum(float(r["modal_price"]) for r in day) / len(day)
            ts, label, state_avg = latest, f"{m['state']} {m['commodity'].lower()}, state average", True
            prev = series[-2][1] if len(series) > 1 and series[-1][0] == latest else None
        day_pct = ((level - float(prev)) / float(prev) * 100) if prev else None
        # the week's move is the state average against itself a week earlier, never the
        # named market against the state, which are two different series
        wk = None
        fresh = series and series[-1][0] >= (datetime.strptime(ts, "%Y-%m-%d") - timedelta(days=5)).strftime("%Y-%m-%d")
        if fresh:      # the history endpoint trails for some crops; a week's move on a stale series is no move
            wk_ago = (datetime.strptime(series[-1][0], "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
            back = next((v for d, v in reversed(series) if d <= wk_ago), None)
            wk = ((series[-1][1] - back) / back * 100) if back else None
        out[cid] = {"kind": "local", "tag": "INDIA", "label": f"{label} · {ts}", "short": label, "detail": m["detail"],
                    "note": m["note"] + ("; the named market had no row in ten days, so this is the state's daily average" if state_avg else ""),
                    "level": round(level, 2), "unit": "₹/qtl", "day_pct": (round(day_pct, 2) if day_pct is not None else None),
                    "wk_pct": (round(wk, 2) if wk is not None else None), "ts": ts, "hist": series[-60:],
                    "source": "Indian Mandi Prices API (agmarknet)", "stale": False}
    if out:
        _cput("mandi_in", out)
        return out
    old = _cold("mandi_in")
    if old and old.get("data"):
        for v in old["data"].values():
            v["stale"] = True
        return old["data"]
    return {}


def mcx_master():
    """Front-month FUTSTK per ShortName: {short: {expiry, unit, lot, name}}."""
    fresh = os.path.exists(MCX_ZIP) and time.time() - os.path.getmtime(MCX_ZIP) < 7 * 86400
    if not fresh:
        try:
            subprocess.run(["curl", "-s", "-m", "120", "-o", MCX_ZIP, MCX_URL],
                           check=False, timeout=150)
        except Exception:  # noqa: BLE001
            pass
    try:
        with zipfile.ZipFile(MCX_ZIP) as z:
            txt = z.read("MCXScripMaster.txt").decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return {}
    today = datetime.now().date()
    best = {}
    for r in csv.DictReader(io.StringIO(txt)):
        if r.get("InstrumentName") != "FUTSTK":
            continue
        try:
            exp = datetime.strptime(r["ExpiryDate"], "%d-%b-%Y").date()
        except (ValueError, KeyError):
            continue
        if exp < today:
            continue
        s = r["ShortName"]
        if s not in best or exp < best[s]["exp"]:
            best[s] = {"exp": exp, "expiry": exp.strftime("%Y-%m-%dT06:00:00.000Z"),
                       "expiry_label": exp.strftime("%d %b %Y"),
                       "unit": MCX_UNIT.get(r.get("PriceUnit", ""), r.get("PriceUnit", "")),
                       "lot": r.get("LotSize"), "name": r.get("ExchangeCode")}
    for v in best.values():
        v.pop("exp", None)
    return best


def _iso(d):
    return d.strftime("%Y-%m-%dT07:00:00.000Z")


def mcx_quotes(client, wanted=None):
    """{short: {level, unit, day_pct, prev, oi, expiry, date, hist}} for the
    front month of each wanted ShortName. Daily candles cached 1h; the
    1-minute tail is fetched every call for the live level."""
    if client is None:
        return {}
    master = mcx_master()
    if not master:
        return {}
    wanted = wanted or sorted(set(MCX_MAP.values()))
    out = {}
    now = datetime.now()
    for short in wanted:
        m = master.get(short)
        if not m:
            continue
        key = f"mcx_{short}_{m['expiry'][:10]}"
        daily = _cget(key, 3600)
        if daily is None:
            try:
                r = client.get_historical_data_v2(
                    interval="1day", from_date=_iso(now - timedelta(days=120)),
                    to_date=_iso(now), stock_code=short, exchange_code="MCX",
                    product_type="futures", expiry_date=m["expiry"],
                    right="others", strike_price="0")
                daily = [{"d": c["datetime"][:10], "c": float(c["close"]),
                          "oi": c.get("open_interest"), "v": c.get("volume")}
                         for c in (r.get("Success") or []) if c.get("close")]
            except Exception:  # noqa: BLE001
                daily = None
            if daily:
                _cput(key, daily)
            else:
                daily = ((_cold(key) or {}).get("data")) or []
        if not daily:
            continue
        level, level_ts = daily[-1]["c"], daily[-1]["d"]
        try:
            r = client.get_historical_data_v2(
                interval="1minute", from_date=_iso(now - timedelta(days=2)),
                to_date=_iso(now + timedelta(days=1)), stock_code=short,
                exchange_code="MCX", product_type="futures",
                expiry_date=m["expiry"], right="others", strike_price="0")
            mins = [c for c in (r.get("Success") or []) if c.get("close")]
            if mins:
                level, level_ts = float(mins[-1]["close"]), mins[-1]["datetime"][:16]
        except Exception:  # noqa: BLE001
            pass
        # previous close = last daily close strictly before the level's day
        prev = None
        for c in reversed(daily):
            if c["d"] < level_ts[:10]:
                prev = c["c"]
                break
        if prev is None and len(daily) > 1:
            prev = daily[-2]["c"]
        out[short] = {
            "short": short, "name": m["name"], "level": level, "unit": m["unit"],
            "prev": prev, "day_pct": ((level / prev - 1) * 100) if prev else None,
            "oi": daily[-1].get("oi"), "expiry": m["expiry_label"], "lot": m["lot"],
            "ts": level_ts, "hist": [(c["d"], c["c"]) for c in daily],
        }
        time.sleep(0.25)
    return out


if __name__ == "__main__":
    print("Rubber Board:", rubber_board())
    from breeze_session import get_client
    q = mcx_quotes(get_client("father"), ["GOLD", "CRUDE", "COPPER"])
    for s, v in q.items():
        print(s, v["level"], v["unit"], v["day_pct"], v["oi"], v["expiry"], v["ts"])
