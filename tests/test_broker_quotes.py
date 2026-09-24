"""Live prices through the Indian brokers, checked without the network.

Each broker's answer below is the example its own documentation prints (Kite Connect
market-quotes, Upstox full market quote, SmartAPI market data, DhanHQ market quote, Groww
live data), cut to the fields the desk reads. The shared instrument list is checked
against a Reliance row as Upstox publishes it.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import brokers  # noqa: E402
from brokers import angel_one, dhan, groww, instruments, upstox, zerodha_kite  # noqa: E402

RELIANCE = {"symbol": "RELIANCE", "exch": "NSE", "isin": "INE002A01018", "token": "2885", "name": "RELIANCE INDUSTRIES LTD"}
BOOK = {"buy": [{"price": 1228.5, "quantity": 40, "orders": 2}], "sell": [{"price": 1228.7, "quantity": 15, "orders": 1}]}


class Answer:
    def __init__(self, status, body):
        self.status_code, self._body = status, body
        self.content = b"x"

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(brokers, "pace", lambda key, gap: None)
    for mod in (zerodha_kite, upstox, angel_one, dhan, groww):
        monkeypatch.setattr(mod, "pace", lambda key, gap: None)
        if hasattr(mod, "instruments"):
            monkeypatch.setattr(mod.instruments, "lookup", lambda code, exch="NSE": dict(RELIANCE, exch=exch))


def _answer(monkeypatch, mod, status, body, sent=None):
    def fake(url, **kw):
        if sent is not None:
            sent.append((url, kw))
        return Answer(status, body)
    monkeypatch.setattr(mod.requests, "get", fake)
    monkeypatch.setattr(mod.requests, "post", fake)


def _client():
    return {"headers": {}}


def test_instrument_list_keeps_equities_only():
    rows = [
        {"segment": "NSE_EQ", "trading_symbol": "RELIANCE", "isin": "INE002A01018", "exchange_token": "2885", "name": "RELIANCE INDUSTRIES LTD"},
        {"segment": "NSE_FO", "trading_symbol": "RELIANCE FUT", "isin": "", "exchange_token": "99", "name": ""},
    ]
    m = instruments.parse(rows, "NSE")
    assert m == {"RELIANCE": ["INE002A01018", "2885", "RELIANCE INDUSTRIES LTD"]}


def test_zerodha_price_and_book(monkeypatch):
    sent = []
    _answer(monkeypatch, zerodha_kite, 200, {"status": "success", "data": {"NSE:RELIANCE": {
        "last_price": 1228.6, "volume": 100, "ohlc": {"open": 1220, "high": 1231, "low": 1218, "close": 1215.0},
        "depth": BOOK}}}, sent)
    q = zerodha_kite.quote(_client(), "RELIANCE", "NSE")
    assert sent[0][1]["params"] == {"i": "NSE:RELIANCE"}
    assert q["ltp"] == 1228.6 and q["prev"] == 1215.0 and q["bid"] == 1228.5 and q["offer"] == 1228.7
    assert round(q["day_pct"], 3) == round((1228.6 - 1215) / 1215 * 100, 3)


def test_zerodha_without_market_data_falls_back_for_the_session(monkeypatch):
    c = _client()
    _answer(monkeypatch, zerodha_kite, 403, {"status": "error", "message": "Insufficient permission for that call.", "error_type": "PermissionException"})
    assert zerodha_kite.quote(c, "RELIANCE", "NSE") is None
    assert brokers.quotes_off(c)
    assert zerodha_kite.quote(c, "TCS", "NSE") is None          # not asked again


def test_zerodha_expired_login_is_not_a_refusal(monkeypatch):
    c = _client()
    _answer(monkeypatch, zerodha_kite, 403, {"status": "error", "message": "Incorrect api_key or access_token.", "error_type": "TokenException"})
    assert zerodha_kite.quote(c, "RELIANCE", "NSE") is None
    assert not brokers.quotes_off(c)


def test_upstox_asks_by_isin_and_backs_out_the_previous_close(monkeypatch):
    sent = []
    _answer(monkeypatch, upstox, 200, {"status": "success", "data": {"NSE_EQ:RELIANCE": {
        "last_price": 52.05, "net_change": -1.05, "volume": 24123697,
        "ohlc": {"open": 53.4, "high": 53.8, "low": 51.75, "close": 52.05}, "depth": BOOK}}}, sent)
    q = upstox.quote(_client(), "RELIANCE", "NSE")
    assert sent[0][1]["params"] == {"instrument_key": "NSE_EQ|INE002A01018"}
    assert q["ltp"] == 52.05 and round(q["prev"], 2) == 53.10 and q["ttq"] == 24123697


def test_angel_asks_by_exchange_number(monkeypatch):
    sent = []
    _answer(monkeypatch, angel_one, 200, {"status": True, "data": {"fetched": [{
        "ltp": 568.2, "open": 567.4, "high": 569.35, "low": 566.1, "close": 567.4,
        "tradeVolume": 3556150, "depth": BOOK}], "unfetched": []}}, sent)
    q = angel_one.quote(_client(), "RELIANCE", "NSE")
    assert sent[0][1]["json"] == {"mode": "FULL", "exchangeTokens": {"NSE": ["2885"]}}
    assert q["ltp"] == 568.2 and q["prev"] == 567.4


def test_dhan_asks_by_exchange_number(monkeypatch):
    sent = []
    _answer(monkeypatch, dhan, 200, {"data": {"NSE_EQ": {"2885": {
        "last_price": 4520, "net_change": 20, "volume": 10,
        "ohlc": {"open": 4500, "close": 4520, "high": 4530, "low": 4490}, "depth": BOOK}}}, "status": "success"}, sent)
    q = dhan.quote(_client(), "RELIANCE", "NSE")
    assert sent[0][1]["json"] == {"NSE_EQ": [2885]}
    assert q["ltp"] == 4520 and q["prev"] == 4500


def test_dhan_without_data_plan_falls_back_for_the_session(monkeypatch):
    c = _client()
    _answer(monkeypatch, dhan, 400, {"errorType": "Invalid_Access", "errorCode": "DH-902", "errorMessage": "User has not subscribed to Data APIs"})
    assert dhan.quote(c, "RELIANCE", "NSE") is None
    assert brokers.quotes_off(c)


def test_groww_reads_its_text_ohlc(monkeypatch):
    sent = []
    _answer(monkeypatch, groww, 200, {"status": "SUCCESS", "payload": {
        "last_price": 149.5, "day_change": -0.5, "volume": 10000,
        "ohlc": "{open: 149.50,high: 150.50,low: 148.50,close: 149.50}", "depth": BOOK}}, sent)
    q = groww.quote(_client(), "RELIANCE", "NSE")
    assert sent[0][1]["params"] == {"exchange": "NSE", "segment": "CASH", "trading_symbol": "RELIANCE"}
    assert q["ltp"] == 149.5 and q["prev"] == 150.0 and q["high"] == 150.5


def test_a_broker_that_prices_nothing_is_let_go(monkeypatch):
    c = _client()
    _answer(monkeypatch, upstox, 500, {"status": "error"})
    for _ in range(brokers.MISS_LIMIT):
        assert upstox.quote(c, "RELIANCE", "NSE") is None
    assert brokers.quotes_off(c)


def test_every_indian_broker_prices():
    for mod in (zerodha_kite, upstox, angel_one, dhan, groww):
        assert callable(getattr(mod, "quote", None)), mod.__name__


# ---- the brokers outside India: answers are the examples in each broker's docs ----------
from brokers import alpaca, questrade, saxo, tastytrade, tradier  # noqa: E402


def test_alpaca_snapshot(monkeypatch):
    sent = []
    _answer(monkeypatch, alpaca, 200, {"latestTrade": {"p": 172.55, "s": 229}, "latestQuote": {"ap": 172.65, "as": 1, "bp": 172.51, "bs": 1},
                                       "dailyBar": {"o": 172.62, "h": 173.71, "l": 171.6618, "c": 173.03, "v": 56457696},
                                       "prevDailyBar": {"c": 173.19}, "symbol": "AAPL"}, sent)
    q = alpaca.quote(_client(), "AAPL")
    assert sent[0][0] == "https://data.alpaca.markets/v2/stocks/AAPL/snapshot"
    assert q["ltp"] == 172.55 and q["prev"] == 173.19 and q["bid"] == 172.51 and q["offer"] == 172.65 and q["ttq"] == 56457696


def test_alpaca_without_the_data_plan_falls_back(monkeypatch):
    c = _client()
    _answer(monkeypatch, alpaca, 403, {"message": "forbidden"})
    assert alpaca.quote(c, "AAPL") is None and brokers.quotes_off(c)


def test_tradier_quote(monkeypatch):
    _answer(monkeypatch, tradier, 200, {"quotes": {"quote": {"symbol": "AAPL", "last": 273.47, "volume": 47994892, "open": 275,
                                                             "high": 275.73, "low": 271.7, "bid": 273.53, "ask": 273.59,
                                                             "prevclose": 275.25, "bidsize": 100, "asksize": 200}}})
    q = tradier.quote({"base": "https://api.tradier.com", "headers": {}}, "AAPL")
    assert q["ltp"] == 273.47 and q["prev"] == 275.25 and q["bid_qty"] == 100


def test_tastytrade_reads_dasherized_text(monkeypatch):
    monkeypatch.setattr(tastytrade, "_access", lambda client: "t")
    _answer(monkeypatch, tastytrade, 200, {"data": {"items": [{"symbol": "AAPL", "bid": "210.55", "bid-size": "2.0", "ask": "210.6",
                                                              "last": "210.511", "open": "208.693", "day-high-price": "212.24",
                                                              "day-low-price": "208.37", "prev-close": "210.14", "volume": "35348839.0"}]}})
    q = tastytrade.quote({"cfg": {}}, "AAPL")
    assert q["ltp"] == 210.511 and q["prev"] == 210.14 and q["high"] == 212.24


def test_questrade_finds_the_number_then_prices(monkeypatch):
    def fake(client, path):
        if path.startswith("v1/symbols/search"):
            return {"symbols": [{"symbol": "THI.TO", "symbolId": 38738}]}
        if path == "v1/symbols/38738":
            return {"symbols": [{"prevDayClosePrice": 83.2}]}
        return {"quotes": [{"symbol": "THI.TO", "bidPrice": 83.65, "bidSize": 6500, "askPrice": 83.67, "askSize": 9100,
                            "lastTradePrice": 83.66, "volume": 80483500, "openPrice": 83.66, "highPrice": 83.86, "lowPrice": 83.66}]}
    monkeypatch.setattr(questrade, "_get", fake)
    q = questrade.quote({}, "THI.TO")
    assert q["ltp"] == 83.66 and q["prev"] == 83.2 and q["offer"] == 83.67


def test_saxo_finds_the_uic_then_prices(monkeypatch):
    def fake(client, path, **params):
        if path == "/ref/v1/instruments":
            return {"Data": [{"Symbol": "AAPL:xmil", "Identifier": 1}, {"Symbol": "AAPL:xnas", "Identifier": 211}]}
        assert params["Uic"] == 211
        return {"Quote": {"Ask": 597, "Bid": 596.5, "Mid": 596.75, "DelayedByMinutes": 15},
                "PriceInfo": {"High": 600, "Low": 590}, "PriceInfoDetails": {"LastTraded": 596.8, "LastClose": 590.1, "Open": 591}}
    monkeypatch.setattr(saxo, "_get", fake)
    q = saxo.quote({}, "AAPL")
    assert q["ltp"] == 596.8 and q["prev"] == 590.1 and q["bid"] == 596.5


def test_brokers_with_no_price_call_say_so_in_their_file():
    # Trading 212 has no quote endpoint, Longbridge prices only over its own socket
    # protocol, Interactive Brokers' Flex service carries statements; these stay on the
    # free feed until a way in exists
    from brokers import ibkr_flex, longbridge, trading212
    for mod in (trading212, longbridge, ibkr_flex):
        assert not hasattr(mod, "quote")
