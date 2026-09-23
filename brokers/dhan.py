"""Dhan (India), through DhanHQ v2. Free for its clients. The reader generates
an access token in My Profile on web.dhan.co and pastes it here; it lasts 24
hours from the moment it is made. An account with TOTP switched on can give the
PIN and the authenticator secret instead, and the desk makes its own token each
time it connects. Reads /v2/profile, /v2/holdings and /v2/fundlimit. Dhan
prices holdings only for accounts on its data plan, so this file returns the
cost side and the desk marks every line from Yahoo. Source: dhanhq.co/docs/v2.

Nothing in this file places a trade."""

import requests

from brokers import BrokerError, derive, num, totp_now

META = {
    "label": "Dhan",
    "where": "India",
    "region": "in",
    "daily_login": False,
    "docs": "https://dhanhq.co/docs/v2/",
    "how": "web.dhan.co, My Profile, Access DhanHQ APIs: generate a token and paste it below with your client id. The token lasts 24 hours. To stop pasting, switch TOTP on for the account and fill the last two boxes instead; the desk then makes its own token.",
    "fields": [
        {"env": "DHAN_CLIENT_ID", "label": "Client id"},
        {"env": "DHAN_ACCESS_TOKEN", "label": "Access token", "secret": True, "required": False,
         "hint": "from My Profile on web.dhan.co; leave empty if you fill the two boxes below"},
        {"env": "DHAN_PIN", "label": "Trading PIN", "secret": True, "required": False,
         "hint": "only for the automatic login"},
        {"env": "DHAN_TOTP_SECRET", "label": "Authenticator secret", "secret": True, "required": False,
         "hint": "the letters behind the TOTP QR code, not the six digits"},
    ],
}

BASE = "https://api.dhan.co/v2"
AUTH = "https://auth.dhan.co/app/generateAccessToken"


def _get(client, path):
    try:
        r = requests.get(BASE + path, headers=client["headers"], timeout=20)
    except requests.RequestException as exc:
        raise BrokerError("Could not reach Dhan: " + str(exc)[:120]) from exc
    if r.status_code in (401, 403):
        raise BrokerError("Dhan did not accept this token. It lasts 24 hours, so make a fresh one in My Profile on web.dhan.co and save it here.")
    if r.status_code == 404:          # DhanHQ answers 404 for an empty book
        return []
    if r.status_code != 200:
        body = (r.text or "")[:160]
        raise BrokerError(f"Dhan answered {r.status_code} for {path}. {body}".strip())
    return r.json() if r.content else []


def _mint(cfg):
    """A token of our own, for an account with TOTP on. Returns None when Dhan will not."""
    try:
        r = requests.get(AUTH, params={"dhanClientId": cfg["DHAN_CLIENT_ID"],
                                       "pin": cfg["DHAN_PIN"],
                                       "totp": totp_now(cfg["DHAN_TOTP_SECRET"], "Dhan")},
                         timeout=20)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    j = r.json() if r.content else {}
    data = j.get("data") if isinstance(j.get("data"), dict) else j
    for key in ("accessToken", "access_token", "token", "jwt"):
        if data.get(key):
            return str(data[key])
    return None


def connect(cfg, token=None):
    tok = ""
    if cfg.get("DHAN_PIN") and cfg.get("DHAN_TOTP_SECRET"):
        tok = _mint(cfg) or ""
    tok = tok or (cfg.get("DHAN_ACCESS_TOKEN") or "").strip()
    if not tok:
        raise BrokerError("Dhan has no token to use. Paste one from My Profile on web.dhan.co, or fill the PIN and the authenticator secret so the desk can make its own.")
    client = {"headers": {"Accept": "application/json", "Content-Type": "application/json",
                          "access-token": tok, "client-id": cfg["DHAN_CLIENT_ID"]}}
    prof = _get(client, "/profile")
    client["profile"] = prof if isinstance(prof, dict) else {}
    return client


def label(client):
    cid = str((client.get("profile") or {}).get("dhanClientId") or client["headers"].get("client-id") or "")
    return f"A/C ··{cid[-4:]}" if len(cid) >= 4 else "account"


def equity(client):
    d = _get(client, "/holdings")
    rows = []
    for h in d if isinstance(d, list) else []:
        exch = (h.get("exchange") or "NSE").upper()
        sym = h.get("tradingSymbol") or ""
        rows.append(derive({
            "code": sym, "name": "", "exch": exch,
            "qty": num(h.get("totalQty")), "avg": num(h.get("avgCostPrice")),
            "ltp": None, "value": None, "pnl": None, "pnl_pct": None, "day_pct": None,
            "currency": "INR", "ysym": sym + (".BO" if exch.startswith("BSE") else ".NS"),
        }))
    return rows


def funds(client):
    d = _get(client, "/fundlimit")
    d = d if isinstance(d, dict) else {}
    # Dhan's own spelling of the balance field is availabelBalance.
    cash = num(d.get("availabelBalance"))
    if cash is None:
        cash = num(d.get("availableBalance"))
    return {"cash": cash, "currency": "INR",
            "buying_power": num(d.get("withdrawableBalance")) or cash}
