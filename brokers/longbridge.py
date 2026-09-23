"""Longbridge (Hong Kong and Singapore), through its OpenAPI. Free for its
clients, and the way into Hong Kong, Singapore and mainland names that most
Western brokers do not reach. Three things from the developer page: an app key,
an app secret and an access token, which Longbridge issues for ninety days at a
time. Every request is signed on this computer with the secret, in the scheme
Longbridge publishes, so the secret itself never travels.

Reads /v1/asset/stock and /v1/asset/account. Positions carry the cost but not
the price, so the desk marks every line from Yahoo. Source:
open.longbridge.com/docs. Nothing here places a trade."""

import hashlib
import hmac
import time

import requests

from brokers import BrokerError, derive, num

META = {
    "label": "Longbridge",
    "where": "Hong Kong and Singapore",
    "region": "hk",
    "daily_login": False,
    "docs": "https://open.longbridge.com/docs",
    "how": "Longbridge's developer page: switch OpenAPI on for the account, then copy the app key, the app secret and the access token. Longbridge issues the token for ninety days; it tells you when it is near the end and a new one goes in the same box.",
    "fields": [
        {"env": "LONGBRIDGE_APP_KEY", "label": "App key", "secret": True},
        {"env": "LONGBRIDGE_APP_SECRET", "label": "App secret", "secret": True},
        {"env": "LONGBRIDGE_ACCESS_TOKEN", "label": "Access token", "secret": True,
         "hint": "Longbridge issues it for ninety days"},
        {"env": "LONGBRIDGE_HOST", "label": "Server address", "required": False,
         "hint": "empty means openapi.longbridge.com; mainland accounts use openapi.longbridge.cn"},
    ],
}

# Longbridge writes a name as ticker.market. Yahoo writes the same share its own way, and
# Hong Kong codes are padded to five digits there.
SUFFIX = {"US": "", "HK": ".HK", "SG": ".SI"}


def _host(cfg):
    got = (cfg.get("LONGBRIDGE_HOST") or "").strip().rstrip("/")
    if not got:
        return "https://openapi.longbridge.com"
    return got if got.startswith("http") else "https://" + got


def _sign(cfg, method, uri, params, headers):
    """Longbridge's own scheme, from its access page: the canonical request is hashed with
    sha1, and that string is what the secret signs with sha256."""
    canonical = (f"{method.upper()}|{uri}|{params}|authorization:{headers['Authorization']}\n"
                 f"x-api-key:{headers['X-Api-Key']}\nx-timestamp:{headers['X-Timestamp']}\n"
                 "|authorization;x-api-key;x-timestamp|")
    sign_str = "HMAC-SHA256|" + hashlib.sha1(canonical.encode("utf-8")).hexdigest()
    signature = hmac.new(cfg["LONGBRIDGE_APP_SECRET"].encode("utf-8"),
                         sign_str.encode("utf-8"), hashlib.sha256).hexdigest()
    return ("HMAC-SHA256 SignedHeaders=authorization;x-api-key;x-timestamp, Signature=" + signature)


def _get(client, uri, params=""):
    cfg = client["cfg"]
    headers = {"Authorization": cfg["LONGBRIDGE_ACCESS_TOKEN"],
               "X-Api-Key": cfg["LONGBRIDGE_APP_KEY"],
               "X-Timestamp": f"{time.time():.3f}",
               "Content-Type": "application/json; charset=utf-8"}
    headers["X-Api-Signature"] = _sign(cfg, "GET", uri, params, headers)
    try:
        r = requests.get(_host(cfg) + uri + (("?" + params) if params else ""),
                         headers=headers, timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Longbridge: " + str(exc)[:120]) from exc
    j = r.json() if r.content else {}
    if r.status_code in (401, 403):
        raise BrokerError("Longbridge did not accept these keys. The access token runs ninety days, so it may have ended; a new one comes from the developer page.")
    if r.status_code != 200 or j.get("code") not in (0, None):
        raise BrokerError("Longbridge answered: " + str(j.get("message") or r.status_code)[:160])
    return j.get("data") or {}


def connect(cfg, token=None):
    client = {"cfg": cfg}
    _get(client, "/v1/asset/account")          # the keys and the signature are proved here
    return client


def label(client):
    # Longbridge's read endpoints name no account number, so there is none to show.
    return "account"


def _ysym(symbol):
    code, _, market = (symbol or "").partition(".")
    market = market.upper()
    if market == "HK" and code.isdigit():
        return code.zfill(4) + ".HK"
    if market == "CN":
        return code + (".SS" if code.startswith("6") else ".SZ")
    return code + SUFFIX.get(market, "")


def equity(client):
    d = _get(client, "/v1/asset/stock")
    rows = []
    for block in (d or {}).get("list") or []:
        for h in block.get("stock_info") or []:
            sym = h.get("symbol") or ""
            rows.append(derive({
                "code": sym, "name": h.get("symbol_name") or "",
                "exch": (h.get("market") or sym.partition(".")[2]).upper(),
                "qty": num(h.get("quantity")), "avg": num(h.get("cost_price")),
                "ltp": None, "value": None, "pnl": None, "pnl_pct": None, "day_pct": None,
                "currency": (h.get("currency") or "").upper(), "ysym": _ysym(sym),
            }))
    return rows


def funds(client):
    rows = (_get(client, "/v1/asset/account") or {}).get("list") or []
    if not rows:
        return {"cash": None, "currency": "HKD", "buying_power": None}
    a = rows[0]
    cash = num(a.get("total_cash"))
    for c in a.get("cash_infos") or []:
        if (c.get("currency") or "").upper() == (a.get("currency") or "").upper():
            cash = num(c.get("available_cash")) or cash
            break
    return {"cash": cash, "currency": (a.get("currency") or "HKD").upper(),
            "buying_power": num(a.get("buy_power")), "equity": num(a.get("net_assets"))}
