"""ICICI Direct, through its Breeze API (India). App key and secret from
api.icicidirect.com (free for its clients) and a login every trading day: the
broker's login page redirects with apisession= in the address, and that value
is the day's token. This is the adapter the desk was first built against, so
it is the one that also serves live ticks, futures and options, margin, and
the index options tape on Desk · Home; the other files in this folder return
holdings and cash. The reads live in collect.py and the session in
breeze_session.py; this file is the door the broker layer opens them through."""

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


def login_url(cfg):
    from urllib.parse import quote
    return "https://api.icicidirect.com/apiuser/login?api_key=" + quote(cfg["BREEZE_API_KEY"], safe="")


def exchange_token(cfg, token):
    return token   # the apisession value is the day's token as it is


def connect(cfg, token=None):
    if not token:
        return None
    from breeze_session import get_client_if_cached
    return get_client_if_cached("primary")   # None when the broker rejects today's token


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
    try:
        import secmaster
        meta = secmaster.lookup(code) or {}
        sym = meta.get("nse_symbol")
        if sym:
            return sym + (".BO" if exch == "BSE" else ".NS")
    except Exception:  # noqa: BLE001
        pass
    return ""


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
