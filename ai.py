"""The reader's own AI, by key. Provider is a setting, not a list: Anthropic,
OpenAI, Google, or any endpoint that speaks the OpenAI chat shape (a model
running on this computer through Ollama or LM Studio, say).

Today this module only proves a key works (the Settings screen's test button).
The Ask box and the Research screen build on the same four settings.
"""

import os

import requests

PROVIDERS = {
    # name: (label, default model, default base url, needs a key)
    "anthropic": ("Anthropic", "claude-opus-5", "https://api.anthropic.com", True),
    "openai": ("OpenAI", "gpt-5", "https://api.openai.com/v1", True),
    "google": ("Google", "gemini-2.5-flash", "https://generativelanguage.googleapis.com/v1beta/openai", True),
    "compatible": ("Any compatible endpoint", "", "", False),
}

_PING = "Reply with the single word: ok"


def settings():
    p = (os.getenv("AI_PROVIDER", "") or "").strip().lower()
    if p not in PROVIDERS:
        p = ""
    label, dmodel, dbase, needs_key = PROVIDERS.get(p, ("", "", "", True))
    return {
        "provider": p,
        "key": (os.getenv("AI_API_KEY", "") or "").strip(),
        "model": (os.getenv("AI_MODEL", "") or "").strip() or dmodel,
        "base_url": (os.getenv("AI_BASE_URL", "") or "").strip() or dbase,
        "needs_key": needs_key,
    }


def _err(r):
    """The endpoint's own words, short, for the page."""
    try:
        j = r.json()
        msg = (j.get("error") or {}).get("message") if isinstance(j.get("error"), dict) else j.get("error") or j.get("message")
        if msg:
            return str(msg)[:240]
    except Exception:  # noqa: BLE001
        pass
    return (r.text or "").strip()[:240] or f"answered {r.status_code}"


def ping(s=None):
    """One tiny request. Returns {'ok': True, 'reply': text} or {'ok': False, 'error': words}."""
    s = s or settings()
    p = s["provider"]
    if not p:
        return {"ok": False, "error": "Pick a provider first."}
    if s["needs_key"] and not s["key"]:
        return {"ok": False, "error": "No AI key saved yet."}
    if not s["model"]:
        return {"ok": False, "error": "Type the model's name; a compatible endpoint does not have a default."}
    if p == "compatible" and not s["base_url"]:
        return {"ok": False, "error": "Type the endpoint's address, for example http://localhost:11434/v1 for Ollama."}
    try:
        if p == "anthropic":
            r = requests.post(s["base_url"].rstrip("/") + "/v1/messages",
                              headers={"x-api-key": s["key"], "anthropic-version": "2023-06-01",
                                       "content-type": "application/json"},
                              json={"model": s["model"], "max_tokens": 16,
                                    "messages": [{"role": "user", "content": _PING}]},
                              timeout=30)
            if r.status_code != 200:
                return {"ok": False, "error": _err(r)}
            j = r.json()
            if j.get("stop_reason") == "refusal":
                return {"ok": True, "reply": "(the model declined the test line, the key itself works)"}
            text = " ".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text").strip()
            return {"ok": True, "reply": text or "(empty reply)"}
        headers = {"content-type": "application/json"}
        if s["key"]:
            headers["authorization"] = "Bearer " + s["key"]
        r = requests.post(s["base_url"].rstrip("/") + "/chat/completions", headers=headers,
                          json={"model": s["model"], "messages": [{"role": "user", "content": _PING}]},
                          timeout=60)
        if r.status_code != 200:
            return {"ok": False, "error": _err(r)}
        j = r.json()
        text = ((j.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return {"ok": True, "reply": str(text).strip() or "(empty reply)"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Nothing answered at " + s["base_url"] + ". Is it running, and is the address right?"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:240]}
