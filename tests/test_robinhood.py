"""Robinhood through its agent server: sign-in, the accounts the reader shows, holdings,
options, cash, crypto and quotes, all in the shapes the server publishes (its tool list
carries an output schema for every tool). Made-up numbers throughout. The desk only reads:
anything outside READS is refused before it leaves the computer."""
import json

import pytest
from requests.structures import CaseInsensitiveDict

import brokers
import brokers.alpaca as alpaca
import brokers.robinhood as rh


class Resp:
    def __init__(self, status, body=None, headers=None):
        self.status_code = status
        self._body = body
        self.headers = CaseInsensitiveDict({"content-type": "application/json", **(headers or {})})
        self.content = b"" if body is None else json.dumps(body).encode()
        self.text = self.content.decode()

    def json(self):
        return self._body


ACCOUNTS = [
    {"account_number": "511112222", "rhs_account_number": "811112222", "type": "margin",
     "brokerage_account_type": "individual", "is_default": True, "agentic_allowed": False, "state": "active"},
    {"account_number": "533334444", "rhs_account_number": "833334444", "type": "cash",
     "brokerage_account_type": "individual", "is_default": False, "agentic_allowed": True, "state": "active"},
]
DATA = {
    ("get_portfolio", "511112222"): {"total_value": "15250.10", "cash": "1200.50", "currency": "USD",
                                     "buying_power": {"buying_power": "2400.00"}},
    ("get_portfolio", "533334444"): {"total_value": "0", "cash": "0", "currency": "USD", "buying_power": {"buying_power": "0"}},
    ("get_equity_positions", "511112222"): {"positions": [
        {"symbol": "AAPL", "quantity": "10.000000", "average_buy_price": "150.250000", "type": "long"},
        {"symbol": "BRK.B", "quantity": "2.500000", "average_buy_price": "400.000000", "type": "long"},
        {"symbol": "OLD", "quantity": "0.000000", "average_buy_price": "5.000000", "type": "long"}]},
    ("get_option_positions", "511112222"): {"positions": [
        {"option_id": "opt-long", "chain_symbol": "AAPL", "type": "long", "quantity": "2.0000",
         "average_price": "150.0000", "trade_value_multiplier": "100.0000", "expiration_date": "2026-12-18"},
        {"option_id": "opt-short", "chain_symbol": "MSFT", "type": "short", "quantity": "1.0000",
         "average_price": "-300.0000", "trade_value_multiplier": "100.0000", "expiration_date": "2026-11-20"}]},
    ("get_option_instruments", None): {"instruments": [
        {"id": "opt-long", "chain_symbol": "AAPL", "strike_price": "200.0000", "type": "call", "expiration_date": "2026-12-18"},
        {"id": "opt-short", "chain_symbol": "MSFT", "strike_price": "400.0000", "type": "put", "expiration_date": "2026-11-20"}]},
    ("get_option_quotes", None): {"results": [
        {"quote": {"instrument_id": "opt-long", "mark_price": "2.1000"}},
        {"quote": {"instrument_id": "opt-short", "mark_price": "1.0000"}}]},
    ("get_crypto_positions", "811112222"): {"results": [
        {"currency": {"code": "BTC", "name": "Bitcoin", "type": "cryptocurrency"}, "quantity": "0.50000000",
         "cost_bases": [{"direct_quantity": "0.40000000", "direct_cost_basis": "24000.00"}]},
        {"currency": {"code": "ETH", "name": "Ethereum", "type": "cryptocurrency"}, "quantity": "2.00000000",
         "cost_bases": [{"direct_quantity": "2.00000000", "direct_cost_basis": "5000.00"}]}]},
    ("get_equity_quotes", None): {"results": [{"quote": {
        "symbol": "AAPL", "last_trade_price": "201.50", "last_non_reg_trade_price": None,
        "adjusted_previous_close": "200.00", "bid_price": "201.45", "bid_size": 300,
        "ask_price": "201.55", "ask_size": 200}}]},
}


@pytest.fixture
def server(monkeypatch, tmp_path):
    """A stand-in for Robinhood: registration, the token endpoint and the agent server."""
    seen = {"calls": [], "tokens": [], "registered": None}
    monkeypatch.setattr(rh, "PENDING", str(tmp_path / "pending.txt"))
    monkeypatch.setattr(rh, "_save", lambda client: seen.setdefault("saved", []).append(dict(client["tok"])))
    state = {"expire_next": False}

    def post(url, json=None, data=None, headers=None, timeout=None):
        if url == rh.REGISTER:
            seen["registered"] = json
            return Resp(201, {"client_id": "desk-client", "redirect_uris": json["redirect_uris"]})
        if url == rh.TOKEN:
            seen["tokens"].append(data)
            n = len(seen["tokens"])
            return Resp(200, {"access_token": f"access-{n}", "refresh_token": f"refresh-{n}", "expires_in": 649589})
        assert url == rh.MCP
        if state["expire_next"]:
            state["expire_next"] = False
            return Resp(401, {"error": "expired"})
        method = json.get("method")
        if method == "initialize":
            return Resp(200, {"jsonrpc": "2.0", "id": 0, "result": {"serverInfo": {"name": "robinhood-trading"}}},
                        {"mcp-session-id": "sess-1"})
        if method == "notifications/initialized":
            return Resp(202)
        name, args = json["params"]["name"], json["params"]["arguments"]
        seen["calls"].append((name, args))
        if name == "get_accounts":
            data = {"accounts": ACCOUNTS}
        else:
            key = args.get("account_number") or args.get("rhs_account_number")
            data = DATA.get((name, key)) or DATA.get((name, None)) or {"positions": [], "results": []}
        return Resp(200, {"jsonrpc": "2.0", "id": json["id"], "result": {"structuredContent": {"data": data, "guide": "..."}}})

    monkeypatch.setattr(rh.requests, "post", post)
    seen["state"] = state
    return seen


TOKEN = json.dumps({"client_id": "desk-client", "redirect": "http://localhost:8765/settings?broker=robinhood",
                    "access": "access-0", "refresh": "refresh-0", "expires": 9e12})


def test_sign_in_registers_the_desk_and_comes_back_to_settings(server):
    url = rh.start_login({}, "http://localhost:8765/settings?broker=robinhood")
    assert server["registered"]["redirect_uris"] == ["http://localhost:8765/settings?broker=robinhood"]
    assert server["registered"]["token_endpoint_auth_method"] == "none"
    assert url.startswith(rh.AUTHORIZE + "?") and "code_challenge_method=S256" in url and "client_id=desk-client" in url
    tok = json.loads(rh.exchange_token({}, "the-code"))
    sent = server["tokens"][-1]
    assert sent["grant_type"] == "authorization_code" and sent["code"] == "the-code" and sent["code_verifier"]
    assert tok["access"] == "access-1" and tok["refresh"] == "refresh-1" and tok["client_id"] == "desk-client"
    with pytest.raises(brokers.BrokerError):
        rh.exchange_token({}, "the-code")          # a code works once; the pending sign-in is gone


def test_the_book_is_the_account_that_holds_something(server):
    cli = rh.connect({}, TOKEN)
    assert [a["account_number"] for a in cli["accounts"]] == ["511112222"]   # the empty Agentic account stays off
    assert rh.label(cli) == "A/C ··2222"
    eq = {r["code"]: r for r in rh.equity(cli)}
    assert set(eq) == {"AAPL", "BRK.B"}                                     # a closed line is dropped
    assert eq["AAPL"]["qty"] == 10 and eq["AAPL"]["avg"] == 150.25 and eq["AAPL"]["ysym"] == "AAPL"
    assert eq["BRK.B"]["ysym"] == "BRK-B"
    f = rh.funds(cli)
    assert (f["cash"], f["buying_power"], f["equity"], f["currency"]) == (1200.5, 2400.0, 15250.1, "USD")


def test_the_reader_names_the_accounts(server):
    cli = rh.connect({"ROBINHOOD_ACCOUNTS": "4444, 2222"}, TOKEN)
    assert [a["account_number"][-4:] for a in cli["accounts"]] == ["2222", "4444"]
    assert list(rh.extra_accounts(cli)) == ["robinhood 4444"]
    with pytest.raises(brokers.BrokerError):
        rh.connect({"ROBINHOOD_ACCOUNTS": "9999"}, TOKEN)


def test_options_price_per_share_with_the_strike_and_side(server):
    cli = rh.connect({}, TOKEN)
    rows = {r["underlying"]: r for r in rh.futures(cli)}
    long_, short = rows["AAPL"], rows["MSFT"]
    assert long_["contract"] == "AAPL 200 Call" and long_["side"] == "Buy" and long_["kind"] == "CE"
    assert (long_["qty"], long_["avg"], long_["ltp"]) == (200.0, 1.5, 2.1)     # 2 contracts x 100, per-share cost
    assert long_["mtm"] == pytest.approx(120.0)                                # (2.10 - 1.50) x 200
    assert short["contract"] == "MSFT 400 Put" and short["side"] == "Sell"
    assert short["mtm"] == pytest.approx(200.0)                                # sold at 3.00, now 1.00, 100 shares


def test_crypto_average_is_the_cost_of_the_units_bought(server):
    cli = rh.connect({}, TOKEN)
    c = {r["code"]: r for r in rh.crypto(cli)}
    assert c["BTC"]["avg"] == pytest.approx(60000.0) and c["BTC"]["avg_partial"] is True   # 0.4 of 0.5 bought
    assert c["ETH"]["avg"] == pytest.approx(2500.0) and c["ETH"]["avg_partial"] is False
    assert c["BTC"]["ysym"] == "BTC-USD" and c["BTC"]["ltp"] is None                       # the free feed marks it


def test_a_live_quote_with_the_book(server):
    cli = rh.connect({}, TOKEN)
    q = rh.quote(cli, "AAPL")
    assert (q["ltp"], q["prev"], q["bid"], q["offer"]) == (201.5, 200.0, 201.45, 201.55)
    assert q["day_pct"] == pytest.approx(0.75)
    assert ("get_equity_quotes", {"symbols": ["AAPL"]}) in server["calls"]


def test_an_expired_key_renews_itself_once_and_is_kept(server):
    cli = rh.connect({}, TOKEN)
    server["state"]["expire_next"] = True
    assert rh.equity(cli)
    assert server["tokens"][-1]["grant_type"] == "refresh_token" and server["tokens"][-1]["refresh_token"] == "refresh-0"
    assert server["saved"][-1]["access"] == "access-1" and server["saved"][-1]["refresh"] == "refresh-1"


def test_the_desk_only_reads(server):
    cli = rh.connect({}, TOKEN)
    for name in ("place_equity_order", "cancel_equity_order", "place_crypto_order", "create_watchlist"):
        with pytest.raises(brokers.BrokerError):
            rh._tool(cli, name, {})
    assert not any(n.startswith(("place_", "cancel_", "create_", "update_", "add_", "remove_", "review_"))
                   for n, _ in server["calls"])
    assert rh.READS == {"get_accounts", "get_portfolio", "get_equity_positions", "get_option_positions",
                        "get_option_instruments", "get_option_quotes", "get_crypto_positions", "get_equity_quotes"}


def test_alpaca_crypto_leaves_the_stock_book_for_the_crypto_block(monkeypatch):
    positions = [{"symbol": "AAPL", "asset_class": "us_equity", "qty": "5", "avg_entry_price": "100"},
                 {"symbol": "BTC/USD", "asset_class": "crypto", "qty": "0.25", "avg_entry_price": "40000"},
                 {"symbol": "ETHUSD", "asset_class": "crypto", "qty": "1", "avg_entry_price": "2000"}]
    monkeypatch.setattr(alpaca, "_get", lambda client, path: positions)
    assert [r["code"] for r in alpaca.equity({})] == ["AAPL"]
    c = {r["code"]: r for r in alpaca.crypto({})}
    assert set(c) == {"BTC", "ETH"} and c["BTC"]["ysym"] == "BTC-USD" and c["BTC"]["avg"] == 40000.0


def test_robinhood_is_on_the_picker_with_nothing_to_paste():
    assert "robinhood" in brokers.REGISTRY
    m = brokers.load("robinhood").META
    assert m["region"] == "us" and m["token_param"] == "code"
    assert all(f.get("required") is False for f in m["fields"])
