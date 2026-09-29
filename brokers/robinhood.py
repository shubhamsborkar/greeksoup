"""Robinhood (United States), through Robinhood's own agent server, the Robinhood Trading
MCP at https://agent.robinhood.com/mcp/trading (launched 27 May 2026). Robinhood opens it
to outside software: the desk registers itself, the reader signs in on Robinhood's page
and presses Allow, and Robinhood sends the reader back to Settings with a sign-in code.
The first time, Robinhood asks the reader to open its Agentic account, which is free and
can stay empty. Access lasts about a week and renews itself from the key Robinhood hands
back, so there is no daily login.

Reads, and only reads: every call goes through READS, eight tools Robinhood itself marks
read-only (readOnlyHint). Stock holdings with the average buy price, options with the
strike from the instrument and the mark from the option quote, cash and buying power,
crypto with the average cost Robinhood's guide defines (direct cost over direct
quantity), and live stock quotes. Several accounts: the first is the book, the others
come through extra_accounts. Sources: robinhood.com/us/en/support/articles/
agentic-trading-overview/ and the server's own tool list with its output schemas.
Nothing in this file places, changes or cancels an order or edits a watchlist."""

import base64
import hashlib
import json
import os
import secrets
import time
from urllib.parse import urlencode

import requests

from brokers import ROOT, BrokerError, derive, last4, num, quote_row

MCP = "https://agent.robinhood.com/mcp/trading"
REGISTER = "https://agent.robinhood.com/oauth/trading/register"
AUTHORIZE = "https://robinhood.com/oauth"
TOKEN = "https://api.robinhood.com/oauth2/token/"
PENDING = os.path.join(ROOT, "session_token_robinhood_pending.txt")   # gitignored: session_token*.txt
READS = {"get_accounts", "get_portfolio", "get_equity_positions", "get_option_positions",
         "get_option_instruments", "get_option_quotes", "get_crypto_positions", "get_equity_quotes"}

META = {
    "label": "Robinhood",
    "where": "United States",
    "region": "us",
    "daily_login": True,
    "login_days": 30,
    "docs": "https://robinhood.com/us/en/support/articles/agentic-trading-overview/",
    "prices": "Live prices: the desk reads the price of every name on your US watchlist and each ticker page from Robinhood's own quotes while you are signed in.",
    "how": "Nothing to copy. Save, then press Log in: Robinhood's page opens and brings you back here by itself. The first time, Robinhood asks you to open its Agentic account; it is free, and you can leave it empty with I'll fund the account later. Then press Allow.",
    "fields": [
        {"env": "ROBINHOOD_ACCOUNTS", "label": "Accounts to show", "required": False,
         "hint": "the last four digits of each, separated by commas; empty shows every account that holds something"},
    ],
    "token_hint": "Log in opens Robinhood's page and brings you back here by itself. If the page you land on does not load, paste its whole address here.",
    "token_param": "code",
}


# ---- sign-in ----------------------------------------------------------------------
def login_url(cfg):
    """The desk's own address that starts the sign-in (the server calls start_login)."""
    return "/broker/login?broker=robinhood"


def start_login(cfg, redirect):
    """Register this desk with Robinhood for this return address, keep the PKCE secret for
    the way back, and hand out Robinhood's sign-in address."""
    try:
        r = requests.post(REGISTER, timeout=20, json={
            "client_name": "GreekSoup desk", "redirect_uris": [redirect],
            "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
            "token_endpoint_auth_method": "none"})
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Robinhood: " + str(exc)[:120]) from exc
    if r.status_code >= 300 or not (r.json() if r.content else {}).get("client_id"):
        raise BrokerError(f"Robinhood did not register the desk ({r.status_code}). Try Log in again in a minute.")
    client_id = r.json()["client_id"]
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    with open(PENDING, "w", encoding="utf-8") as fh:
        json.dump({"client_id": client_id, "verifier": verifier, "state": state,
                   "redirect": redirect, "at": time.time()}, fh)
    return AUTHORIZE + "?" + urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": redirect,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
        "scope": "internal", "resource": MCP})


def _token_call(form):
    try:
        r = requests.post(TOKEN, data=form, timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Robinhood: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code != 200 or not j.get("access_token"):
        raise BrokerError("Robinhood did not accept that sign-in ("
                          + str(j.get("error_description") or j.get("error") or r.status_code)[:120]
                          + "). Press Log in again; a sign-in code works once.")
    return j


def _keep(j, client_id, redirect):
    return {"client_id": client_id, "redirect": redirect, "access": j["access_token"],
            "refresh": j.get("refresh_token") or "",
            "expires": time.time() + float(j.get("expires_in") or 3600)}


def exchange_token(cfg, raw):
    try:
        with open(PENDING, encoding="utf-8") as fh:
            p = json.load(fh)
    except (OSError, ValueError):
        raise BrokerError("This sign-in was not started from this desk, or it has already been used. Press Log in again.") from None
    code = str(raw or "").strip()
    j = _token_call({"grant_type": "authorization_code", "code": code, "redirect_uri": p["redirect"],
                     "client_id": p["client_id"], "code_verifier": p["verifier"], "resource": MCP})
    try:
        os.remove(PENDING)
    except OSError:
        pass
    return json.dumps(_keep(j, p["client_id"], p["redirect"]))


def _save(client):
    from brokers import write_token
    write_token(json.dumps(client["tok"]), "robinhood")


def _fresh(client):
    """A live access key, renewed from Robinhood's refresh key when it is about to lapse."""
    t = client["tok"]
    if t.get("access") and time.time() < t.get("expires", 0) - 300:
        return t["access"]
    if not t.get("refresh"):
        raise BrokerError("Robinhood's access has lapsed. Press Log in again.")
    j = _token_call({"grant_type": "refresh_token", "refresh_token": t["refresh"], "client_id": t["client_id"]})
    client["tok"] = {**_keep(j, t["client_id"], t.get("redirect", "")), "refresh": j.get("refresh_token") or t["refresh"]}
    client.pop("session", None)
    _save(client)
    return client["tok"]["access"]


# ---- the agent server ---------------------------------------------------------------
def _post(client, payload, retried=False):
    headers = {"Authorization": "Bearer " + _fresh(client), "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if client.get("session"):
        headers["Mcp-Session-Id"] = client["session"]
    try:
        r = requests.post(MCP, headers=headers, json=payload, timeout=40)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Robinhood: " + str(exc)[:120]) from exc
    if r.status_code == 401 and not retried:
        client["tok"]["expires"] = 0          # renew once, then ask again
        return _post(client, payload, True)
    if r.status_code == 404 and client.get("session") and not retried:
        client.pop("session", None)           # the server forgot the session: start another
        _init(client)
        return _post(client, payload, True)
    if r.status_code in (401, 403):
        raise BrokerError("Robinhood refused the desk's access. Press Log in again, or check it is still allowed in Robinhood's Security & Privacy settings.")
    if r.status_code >= 300:
        raise BrokerError(f"Robinhood answered {r.status_code}.")
    if r.headers.get("mcp-session-id"):
        client["session"] = r.headers["mcp-session-id"]
    if not r.content:
        return {}
    if "text/event-stream" in r.headers.get("content-type", ""):
        last = {}
        for ln in r.text.splitlines():
            if ln.startswith("data:"):
                try:
                    last = json.loads(ln[5:].strip())
                except ValueError:
                    pass
        return last
    return r.json()


def _init(client):
    client["n"] = 0
    _post(client, {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "GreekSoup desk", "version": "1"}}}, True)
    _post(client, {"jsonrpc": "2.0", "method": "notifications/initialized"}, True)


def _tool(client, name, args=None):
    """One read. Anything outside READS is refused here, before it reaches Robinhood."""
    if name not in READS:
        raise BrokerError(f"The desk only reads; {name} is not one of its reads.")
    if not client.get("session"):
        _init(client)
    client["n"] = client.get("n", 0) + 1
    r = _post(client, {"jsonrpc": "2.0", "id": client["n"], "method": "tools/call",
                       "params": {"name": name, "arguments": args or {}}})
    if r.get("error"):
        raise BrokerError("Robinhood could not answer " + name + ": " + str((r["error"] or {}).get("message", ""))[:160])
    res = r.get("result") or {}
    out = res.get("structuredContent")
    if out is None:
        for c in res.get("content") or []:
            try:
                out = json.loads(c.get("text", ""))
            except ValueError:
                out = {"_text": c.get("text", "")}
    if res.get("isError"):
        raise BrokerError("Robinhood could not answer " + name + ": " + str((out or {}).get("_text") or out)[:160])
    return (out or {}).get("data") or {}


def _pages(client, name, args, key):
    rows, cursor = [], None
    for _ in range(20):
        d = _tool(client, name, {**args, **({"cursor": cursor} if cursor else {})})
        rows += d.get(key) or []
        cursor = d.get("next")
        if not cursor:
            break
    return rows


# ---- the desk's contract ----------------------------------------------------------------
def connect(cfg, token=None):
    if not token:
        return None
    try:
        tok = json.loads(token)
    except ValueError:
        raise BrokerError("The saved Robinhood sign-in could not be read. Press Log in again.") from None
    client = {"tok": tok, "cfg": cfg}
    accounts = [a for a in (_tool(client, "get_accounts").get("accounts") or [])
                if a.get("state", "active") == "active" and not a.get("deactivated")]
    if not accounts:
        raise BrokerError("Robinhood shows no open account on this sign-in.")
    want = [w.strip()[-4:] for w in (cfg.get("ROBINHOOD_ACCOUNTS") or "").split(",") if w.strip()]
    accounts.sort(key=lambda a: (not a.get("is_default"), not a.get("agentic_allowed")))
    if want:
        chosen = [a for a in accounts if str(a.get("account_number", ""))[-4:] in want]
        if not chosen:
            raise BrokerError("None of the accounts on Settings (" + ", ".join(want) + ") is on this Robinhood sign-in.")
    else:
        chosen = []
        for a in accounts:              # every account that holds something; an empty one stays off the desk
            v = num(_tool(client, "get_portfolio", {"account_number": a["account_number"]}).get("total_value"))
            if v or a.get("is_default"):
                chosen.append(a)
    client["accounts"] = chosen or accounts[:1]
    return client


def label(client):
    return last4(client["accounts"][0].get("account_number"))


def _nick(a):
    t = (a.get("nickname") or a.get("brokerage_account_type") or "account").replace("_", " ")
    return f"{last4(a.get('account_number'))} · {t}"


def _equity(client, a):
    rows = []
    for p in _pages(client, "get_equity_positions", {"account_number": a["account_number"]}, "positions"):
        qty = num(p.get("quantity"))
        sym = p.get("symbol") or ""
        if not qty or not sym:
            continue
        rows.append(derive({"code": sym, "name": "", "exch": "", "qty": qty,
                            "avg": num(p.get("average_buy_price")), "ltp": None, "value": None,
                            "pnl": None, "pnl_pct": None, "day_pct": None,
                            "currency": "USD", "ysym": sym.replace(".", "-")}))
    return rows


def _options(client, a):
    pos = [p for p in _pages(client, "get_option_positions",
                             {"account_number": a["account_number"], "nonzero": True}, "positions")
           if num(p.get("quantity"))]
    if not pos:
        return []
    ids = ",".join(p["option_id"] for p in pos if p.get("option_id"))
    inst = {i.get("id"): i for i in _pages(client, "get_option_instruments", {"ids": ids}, "instruments")}
    marks = {}
    for q in (_tool(client, "get_option_quotes", {"instrument_ids": ids.split(",")}).get("results") or []):
        q = (q or {}).get("quote") or {}
        if q.get("instrument_id"):
            marks[q["instrument_id"]] = num(q.get("mark_price"))
    out = []
    for p in pos:
        i = inst.get(p.get("option_id")) or {}
        mult = num(p.get("trade_value_multiplier")) or 100.0
        contracts = num(p.get("quantity")) or 0.0
        long_ = (p.get("type") or "long") == "long"
        sign = 1 if long_ else -1
        qty = contracts * mult                                   # shares, the desk's unit for a contract
        avg = abs(num(p.get("average_price")) or 0.0) / mult     # Robinhood's is per contract and signed
        ltp = marks.get(p.get("option_id"))
        mtm = (ltp - avg) * qty * sign if ltp is not None else None
        strike = num(i.get("strike_price"))
        kind = "CE" if i.get("type") == "call" else ("PE" if i.get("type") == "put" else "OPT")
        und = i.get("chain_symbol") or p.get("chain_symbol") or ""
        out.append({"underlying": und,
                    "contract": f"{und} {strike:g} {'Call' if kind == 'CE' else 'Put' if kind == 'PE' else 'Option'}" if strike else f"{und} option",
                    "kind": kind, "right": i.get("type") or "", "strike": strike or 0,
                    "expiry": i.get("expiration_date") or p.get("expiration_date"),
                    "side": "Buy" if long_ else "Sell", "qty": qty, "avg": avg, "ltp": ltp, "mtm": mtm,
                    "mtm_pct": ((ltp - avg) / avg * 100 * sign) if (ltp is not None and avg) else None,
                    "notional": (ltp * qty) if ltp is not None else None})
    return out


def _funds(client, a):
    d = _tool(client, "get_portfolio", {"account_number": a["account_number"]})
    return {"cash": num(d.get("cash")), "currency": d.get("currency") or "USD",
            "buying_power": num((d.get("buying_power") or {}).get("buying_power")),
            "equity": num(d.get("total_value"))}


def _crypto(client, a):
    rhs = a.get("rhs_account_number")
    if not rhs:
        return []
    rows = []
    for p in _pages(client, "get_crypto_positions", {"rhs_account_number": rhs}, "results"):
        cur = (p or {}).get("currency") or {}
        code = cur.get("code") or ""
        qty = num(p.get("quantity"))
        if not code or not qty or cur.get("type") == "fiat":
            continue
        dq = sum(num(c.get("direct_quantity")) or 0 for c in p.get("cost_bases") or [])
        dc = sum(num(c.get("direct_cost_basis")) or 0 for c in p.get("cost_bases") or [])
        rows.append({"code": code, "name": cur.get("name") or code, "exch": "Robinhood", "qty": qty,
                     "avg": (dc / dq) if dq else None,
                     # the average covers bought units only; transfers and rewards carry no cost
                     "avg_partial": bool(dq) and dq < qty * 0.999,
                     "ltp": None, "value": None, "pnl": None, "pnl_pct": None, "day_pct": None,
                     "currency": "USD", "ysym": f"{code}-USD"})
    return rows


def equity(client):
    return _equity(client, client["accounts"][0])


def futures(client):
    return _options(client, client["accounts"][0])


def funds(client):
    return _funds(client, client["accounts"][0])


def crypto(client):
    return _crypto(client, client["accounts"][0])


def extra_accounts(client, live_names=None):
    """The other Robinhood accounts the reader shows: each its own block on Desk · Home."""
    out = {}
    for a in client["accounts"][1:]:
        out["robinhood " + str(a.get("account_number", ""))[-4:]] = {
            "label": _nick(a), "broker": META["label"], "region": "us", "currency": "USD",
            "equity": _equity(client, a), "futures": _options(client, a),
            "funds": _funds(client, a), "crypto": _crypto(client, a)}
    return out


def quote(client, code, exch=None):
    d = _tool(client, "get_equity_quotes", {"symbols": [code]})
    for r in d.get("results") or []:
        q = (r or {}).get("quote") or {}
        if (q.get("symbol") or "").upper() == code.upper():
            ltp = num(q.get("last_trade_price"))
            ext = num(q.get("last_non_reg_trade_price"))
            return quote_row(code, exch or "", ext or ltp, prev=num(q.get("adjusted_previous_close")) or num(q.get("previous_close")),
                             depth={"buy": [{"price": q.get("bid_price"), "quantity": q.get("bid_size")}],
                                    "sell": [{"price": q.get("ask_price"), "quantity": q.get("ask_size")}]})
    return None
