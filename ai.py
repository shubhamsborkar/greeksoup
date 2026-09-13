"""The reader's own AI, by key. Two request shapes exist in the world today and
the desk speaks both: the OpenAI chat shape (POST .../chat/completions, used by
OpenAI, Google's compatible endpoint, xAI, Mistral, OpenRouter, Ollama, LM Studio
and most others) and the Anthropic messages shape (POST .../v1/messages, used by
Anthropic and offered as a second door by DeepSeek, Kimi, MiniMax, Z.ai and
Alibaba's Qwen). A preset fills the format, the address and a starting model;
any of the three can be changed, and "any other endpoint" takes all three by hand.

Today this module proves a key works (the Settings screen's test button). The
Ask box and the Research screen build on the same settings.
"""

import os

import requests

FORMATS = {
    "openai": "OpenAI chat shape (.../chat/completions)",
    "anthropic": "Anthropic messages shape (.../v1/messages)",
}

# id -> preset. base_url ends where the format's path is appended.
# model "" = the reader types the name from the provider's model page.
PROVIDERS = {
    "anthropic":  {"label": "Anthropic", "format": "anthropic", "base_url": "https://api.anthropic.com", "model": "claude-opus-5", "needs_key": True},
    "openai":     {"label": "OpenAI", "format": "openai", "base_url": "https://api.openai.com/v1", "model": "gpt-5", "needs_key": True},
    "google":     {"label": "Google (Gemini)", "format": "openai", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-3.8-flash", "needs_key": True},
    "deepseek":   {"label": "DeepSeek", "format": "openai", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat", "needs_key": True,
                   "alt": {"format": "anthropic", "base_url": "https://api.deepseek.com/anthropic"}},
    "kimi":       {"label": "Kimi (Moonshot)", "format": "openai", "base_url": "https://api.moonshot.ai/v1", "model": "kimi-k3", "needs_key": True,
                   "alt": {"format": "anthropic", "base_url": "https://api.moonshot.ai/anthropic"}},
    "minimax":    {"label": "MiniMax", "format": "anthropic", "base_url": "https://api.minimax.io/anthropic", "model": "", "needs_key": True,
                   "alt": {"format": "openai", "base_url": "https://api.minimax.io/v1"}},
    "zai":        {"label": "Z.ai (GLM)", "format": "anthropic", "base_url": "https://api.z.ai/api/anthropic", "model": "", "needs_key": True},
    "qwen":       {"label": "Alibaba (Qwen)", "format": "anthropic", "base_url": "https://dashscope-intl.aliyuncs.com/apps/anthropic", "model": "", "needs_key": True},
    "xai":        {"label": "xAI (Grok)", "format": "openai", "base_url": "https://api.x.ai/v1", "model": "", "needs_key": True},
    "mistral":    {"label": "Mistral", "format": "openai", "base_url": "https://api.mistral.ai/v1", "model": "", "needs_key": True},
    "openrouter": {"label": "OpenRouter (many models, one key)", "format": "openai", "base_url": "https://openrouter.ai/api/v1", "model": "", "needs_key": True},
    "ollama":     {"label": "Ollama on this computer", "format": "openai", "base_url": "http://localhost:11434/v1", "model": "", "needs_key": False},
    "lmstudio":   {"label": "LM Studio on this computer", "format": "openai", "base_url": "http://localhost:1234/v1", "model": "", "needs_key": False},
    "custom":     {"label": "Any other endpoint", "format": "openai", "base_url": "", "model": "", "needs_key": False},
}

_PING = "Reply with the single word: ok"


def settings():
    p = (os.getenv("AI_PROVIDER", "") or "").strip().lower()
    preset = PROVIDERS.get(p, {})
    fmt = (os.getenv("AI_FORMAT", "") or "").strip().lower() or preset.get("format", "openai")
    if fmt not in FORMATS:
        fmt = "openai"
    return {
        "provider": p if p in PROVIDERS else "",
        "format": fmt,
        "key": (os.getenv("AI_API_KEY", "") or "").strip(),
        "model": (os.getenv("AI_MODEL", "") or "").strip() or preset.get("model", ""),
        "base_url": (os.getenv("AI_BASE_URL", "") or "").strip() or preset.get("base_url", ""),
        "needs_key": preset.get("needs_key", False),
    }


def _err(r):
    """The endpoint's own words, short, for the page."""
    try:
        j = r.json()
        e = j.get("error")
        msg = e.get("message") if isinstance(e, dict) else (e or j.get("message"))
        if msg:
            return str(msg)[:240]
    except Exception:  # noqa: BLE001
        pass
    return (r.text or "").strip()[:240] or f"answered {r.status_code}"


def _anthropic(s, bearer=False):
    headers = {"anthropic-version": "2023-06-01", "content-type": "application/json"}
    if s["key"]:
        if bearer:
            headers["authorization"] = "Bearer " + s["key"]
        else:
            headers["x-api-key"] = s["key"]
    return requests.post(s["base_url"].rstrip("/") + "/v1/messages", headers=headers,
                         json={"model": s["model"], "max_tokens": 16,
                               "messages": [{"role": "user", "content": _PING}]},
                         timeout=45)


def ping(s=None):
    """One tiny request. {'ok': True, 'reply': text} or {'ok': False, 'error': words}."""
    s = s or settings()
    if not s["provider"]:
        return {"ok": False, "error": "Pick a provider first."}
    if s["needs_key"] and not s["key"]:
        return {"ok": False, "error": "No AI key saved yet."}
    if not s["model"]:
        return {"ok": False, "error": "Type the model's name; this provider's page lists them."}
    if not s["base_url"]:
        return {"ok": False, "error": "Type the endpoint's address."}
    try:
        if s["format"] == "anthropic":
            r = _anthropic(s)
            if r.status_code == 401 and s["key"]:
                r = _anthropic(s, bearer=True)   # a few compatible endpoints want Bearer
            if r.status_code != 200:
                return {"ok": False, "error": _err(r)}
            j = r.json()
            if j.get("stop_reason") == "refusal":
                return {"ok": True, "reply": "(the model declined the test line; the key itself works)"}
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
