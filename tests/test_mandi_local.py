"""The India local layer of the Commodities board: the benchmark mandi's row wins, the
state average stands in when the market has no recent row and says so, the week's
move is the state series against itself and only when that series is current."""
import local_in


def _fetch(rows, hist):
    def get(url, params):
        return hist if url.endswith("/history") else rows
    return get


def test_benchmark_market_row_wins(monkeypatch, tmp_path):
    monkeypatch.setattr(local_in, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(local_in, "MANDI_MAP", {"cotton": local_in.MANDI_MAP["cotton"]})
    rows = [{"market": "Raichur APMC", "variety": "H4", "arrival_date": "2026-09-18", "modal_price": 9811},
            {"market": "Raichur APMC", "variety": "H4", "arrival_date": "2026-09-17", "modal_price": 9600},
            {"market": "Raichur APMC", "variety": "Bunny", "arrival_date": "2026-09-18", "modal_price": 12000},
            {"market": "Kustagi APMC", "variety": "Other", "arrival_date": "2026-09-18", "modal_price": 9845}]
    hist = [{"arrival_date": "2026-09-11", "avg_modal_price": 9214}, {"arrival_date": "2026-09-18", "avg_modal_price": 9237}]
    out = local_in.mandi_prices(fetch=_fetch(rows, hist))
    c = out["cotton"]
    assert c["level"] == 9811 and c["unit"] == "₹/qtl" and c["ts"] == "2026-09-18"
    assert c["short"] == "Raichur kapas (seed cotton)" and "state" not in c["note"]
    assert round(c["day_pct"], 2) == round((9811 - 9600) / 9600 * 100, 2)
    assert round(c["wk_pct"], 2) == round((9237 - 9214) / 9214 * 100, 2)
    assert c["hist"][-1] == ["2026-09-18", 9237.0] and c["stale"] is False


def test_state_average_stands_in_and_says_so(monkeypatch, tmp_path):
    monkeypatch.setattr(local_in, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(local_in, "MANDI_MAP", {"wheat": local_in.MANDI_MAP["wheat"]})
    rows = [{"market": "Indore APMC", "variety": "Mill Quality", "arrival_date": "2026-08-01", "modal_price": 2500},   # too old
            {"market": "Sehore APMC", "variety": "Lokwan", "arrival_date": "2026-09-18", "modal_price": 2800},
            {"market": "Ujjain APMC", "variety": "Mill Quality", "arrival_date": "2026-09-18", "modal_price": 2600}]
    hist = [{"arrival_date": "2026-07-31", "avg_modal_price": 2581}]      # the history trails, so no week move
    out = local_in.mandi_prices(fetch=_fetch(rows, hist))
    w = out["wheat"]
    assert w["level"] == 2700 and w["ts"] == "2026-09-18"
    assert w["short"] == "Madhya Pradesh wheat, state average" and "state's daily average" in w["note"]
    assert w["wk_pct"] is None and w["day_pct"] is None


def test_failed_fetch_returns_the_last_sheet_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(local_in, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(local_in, "MANDI_MAP", {"cotton": local_in.MANDI_MAP["cotton"]})
    rows = [{"market": "Raichur APMC", "variety": "H4", "arrival_date": "2026-09-18", "modal_price": 9811}]
    assert local_in.mandi_prices(fetch=_fetch(rows, []))["cotton"]["level"] == 9811
    import json, os, time
    p = os.path.join(str(tmp_path), "mandi_in.json")
    c = json.load(open(p)); c["at"] = time.time() - 10 * 3600; json.dump(c, open(p, "w"))     # the cache has aged out
    out = local_in.mandi_prices(fetch=lambda url, params: (_ for _ in ()).throw(RuntimeError("asleep")))
    assert out["cotton"]["level"] == 9811 and out["cotton"]["stale"] is True


def test_india_market_attaches_lines_without_a_broker(monkeypatch):
    import importlib
    m = importlib.import_module("markets.in")
    monkeypatch.setattr(local_in, "mandi_prices", lambda: {"cotton": {"kind": "local", "short": "Raichur kapas (seed cotton)", "level": 9811, "unit": "₹/qtl"}})
    monkeypatch.setattr(local_in, "rubber_board", lambda: {"date": "2026-09-19", "grades": {"RSS4": {"inr_per_kg": 274.0, "usc_per_kg": 311.0}}})
    cards = [{"id": "cotton"}, {"id": "rubber", "local": [{"kind": "local", "short": "Kottayam RSS4", "level": 270.0}]}, {"id": "gold"}]
    assert m.commodities_local(cards) is True
    assert cards[0]["local"][0]["short"] == "Raichur kapas (seed cotton)"
    assert len(cards[1]["local"]) == 1 and cards[1]["local"][0]["level"] == 270.0      # the broker's line already there is kept, not doubled
    assert "local" not in cards[2]
