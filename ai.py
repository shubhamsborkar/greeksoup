"""The reader's own AI, by key. Two request shapes exist in the world today and
the desk speaks both: the OpenAI chat shape (POST .../chat/completions, used by
OpenAI, Google's compatible endpoint, xAI, Mistral, OpenRouter, Ollama, LM Studio
and most others) and the Anthropic messages shape (POST .../v1/messages, used by
Anthropic and offered as a second door by DeepSeek, Kimi, MiniMax, Z.ai and
Alibaba's Qwen). A preset fills the format, the address and a starting model;
any of the three can be changed, and "any other endpoint" takes all three by hand.

Two things use it: the Settings screen's test button (ping), and the Ask box on
every screen (ask), which sends the reader's question with the numbers of the
screen they are on and shows the answer. Nothing here places an order or reads
a key back.
"""

import base64
import os

import requests

FORMATS = {
    "openai": "the common way (most labs, every local model)",
    "anthropic": "Anthropic's own way",
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


def _anthropic(s, messages, system=None, max_tokens=16, bearer=False, timeout=45, web=False):
    headers = {"anthropic-version": "2023-06-01", "content-type": "application/json"}
    if s["key"]:
        if bearer:
            headers["authorization"] = "Bearer " + s["key"]
        else:
            headers["x-api-key"] = s["key"]
    body = {"model": s["model"], "max_tokens": max_tokens, "messages": messages}
    if system:
        body["system"] = system
    if web:
        # Anthropic's own web search, run on their side; the answer carries citations
        body["tools"] = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 6}]
    return requests.post(s["base_url"].rstrip("/") + "/v1/messages", headers=headers, json=body, timeout=timeout)


def web_ready(s=None):
    """Whether the key on Settings can search the web through the way the desk speaks to it:
    Anthropic's own endpoint has a search tool; the common way has none. Words when it cannot."""
    s = s or settings()
    if s["format"] == "anthropic" and "anthropic.com" in (s.get("base_url") or ""):
        return None
    return f"{PROVIDERS.get(s['provider'], {}).get('label') or 'This provider'} cannot search the web through the desk; an app on this computer (Claude Code, Codex, Gemini CLI) or an Anthropic key can."


def _openai(s, messages, system=None, max_tokens=None, timeout=60):
    headers = {"content-type": "application/json"}
    if s["key"]:
        headers["authorization"] = "Bearer " + s["key"]
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    body = {"model": s["model"], "messages": msgs}
    if max_tokens:
        body["max_tokens"] = max_tokens
    return requests.post(s["base_url"].rstrip("/") + "/chat/completions", headers=headers, json=body, timeout=timeout)


def not_ready(s):
    """Why a request cannot be made yet, in the reader's words, or None."""
    if not s["provider"]:
        return "Pick a provider first."
    if s["needs_key"] and not s["key"]:
        return "No AI key saved yet."
    if not s["model"]:
        return "Type the model's name; this provider's page lists them."
    if not s["base_url"]:
        return "Type the endpoint's address."
    return None


def complete(messages, system=None, max_tokens=16, timeout=60, s=None, web=False):
    """One request in whichever shape the endpoint speaks.
    {'ok': True, 'text': ...} or {'ok': False, 'error': words}."""
    s = s or settings()
    why = not_ready(s)
    if why:
        return {"ok": False, "error": why}
    if web:
        why = web_ready(s)
        if why:
            return {"ok": False, "error": why}
    try:
        if s["format"] == "anthropic":
            r = _anthropic(s, messages, system, max_tokens, timeout=timeout, web=web)
            if r.status_code == 401 and s["key"]:
                r = _anthropic(s, messages, system, max_tokens, bearer=True, timeout=timeout, web=web)   # a few compatible endpoints want Bearer
            if r.status_code != 200:
                return {"ok": False, "error": _err(r)}
            j = r.json()
            if j.get("stop_reason") == "refusal":
                return {"ok": True, "text": "", "refused": True}
            blocks = [b for b in j.get("content", []) if b.get("type") == "text"]
            text = " ".join(b.get("text", "") for b in blocks).strip()
            # the pages the search read, as the answer cites them
            seen, sources = set(), []
            for b in blocks:
                for c in b.get("citations") or []:
                    u = c.get("url")
                    if u and u not in seen:
                        seen.add(u)
                        sources.append({"url": u, "title": c.get("title") or u})
            return {"ok": True, "text": text, "sources": sources}
        r = _openai(s, messages, system, max_tokens if max_tokens > 16 else None, timeout=timeout)
        if r.status_code != 200:
            return {"ok": False, "error": _err(r)}
        j = r.json()
        text = ((j.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return {"ok": True, "text": str(text).strip()}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Nothing answered at " + s["base_url"] + ". Is it running, and is the address right?"}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "The model did not answer in time. Try once more, or a smaller model."}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:240]}


def ping(s=None):
    """One tiny request. {'ok': True, 'reply': text} or {'ok': False, 'error': words}."""
    out = complete([{"role": "user", "content": _PING}], max_tokens=16, s=s)
    if not out["ok"]:
        return out
    if out.get("refused"):
        return {"ok": True, "reply": "(the model declined the test line; the key itself works)"}
    return {"ok": True, "reply": out["text"] or "(empty reply)"}


ASK_SYSTEM = """You are SuperAnalyst, the AI inside GreekSoup, the one-person equity research desk, which runs on the reader's computer. The reader is on the screen named below. That screen's numbers follow as JSON, exactly as the desk holds them, and after them the other screens the question points at, each under its address.

Answer from those numbers, in plain words, in a few short paragraphs. When you use a figure, say which screen and source it came from. When the data includes the reader's own notes or documents (their research vault), treat them as the reader's work: quote a note or a file by its title when you draw on it, and never present the reader's own view back to them as the model's finding. The desk is one connected thing: a question asked on one screen is often answered on another, and the map of the whole desk is below. If the answer needs a screen you were not handed, reply with exactly one line and nothing else: NEED: followed by the addresses from the map, separated by spaces (for one listing, /api/ticker?symbol=AAPL&region=us and /api/research/context?symbol=AAPL). You will be handed them and asked again. Never invent a figure the data does not carry; when even the map has no screen for it, say so plainly instead of guessing. Describe what the numbers show; never tell the reader what to buy, sell or hold. Currencies and units are as the data gives them. Keep it short."""

BUILD_SYSTEM = """You are SuperAnalyst, working inside GreekSoup, the one-person equity research desk, which runs from the folder you are in on the reader's own computer. The reader has switched you from Research to Build: they are asking you to change the desk itself, and you may read and edit files in this folder to do it. The rules: change only what the reader asked for, and say plainly what you changed, file by file, when you are done; the folder data/ holds the reader's own book, watchlists, keys and research vault, never delete or rewrite those beyond the edit asked for; never send anything outside this computer, never touch a broker, and never place an order; if a Python file changed, say that the desk needs a restart to pick it up. If the request is unclear or would reach outside this folder, say so and stop instead of guessing. What the desk is and how it is laid out follows."""


WEB_LINE = ("You may also search the web for what the desk does not hold: filings, news, the company's own pages, "
            "the regulator's record. The desk's numbers come first and are named as such; every fact from the web "
            "carries its source as a link, and a figure you could not verify is said to be unverified.")


def pictures_text(pictures):
    """The reader's pictures on the subject, for an app that can open files on this computer."""
    if not pictures:
        return ""
    lines = [f"- {p['path']}  ({p['title']}" + (f", {p['period']}" if p.get("period") else "") + (f", kept {p['updated']}" if p.get("updated") else "") + ")" for p in pictures]
    return ("\n\nTHE READER'S PICTURES ON THIS SUBJECT (chart clippings and screenshots they kept in their notes; open and look at each file before answering, and quote it by its title)\n" + "\n".join(lines))


def _image_block(p, fmt):
    """One picture as the provider's own image block, or None when the file cannot be read."""
    try:
        with open(p["path"], "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
    except OSError:
        return None
    mt = p.get("media_type") or "image/png"
    if fmt == "anthropic":
        return {"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}}
    return {"type": "image_url", "image_url": {"url": f"data:{mt};base64,{data}"}}


def door_prompt(question, screen, context, profile="", history=None, desk_map="", web=False, pictures=None):
    """The same brief the Ask box gives a provider, as one text for a door: a command on the
    reader's computer (their coding agent) that reads standard input and answers on standard output."""
    text = ASK_SYSTEM + "\n\nSCREEN: " + screen
    if profile:
        text += "\n\nHOW THIS READER INVESTS (from their Settings screen; shape answers to it)\n" + profile
    if desk_map:
        text += "\n\nTHE WHOLE DESK (address, screen, what it holds)\n" + desk_map
    text += "\n\nTHE DATA (this screen first, then the screens the question points at)\n" + context
    text += pictures_text(pictures)
    turns = [m for m in (history or []) if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)][-6:]
    if turns:
        text += "\n\nTHE CONVERSATION SO FAR\n" + "\n".join(f"{m['role'].upper()}: {m['content']}" for m in turns)
    if web:
        text += "\n\nTHE QUESTION\n" + question + "\n\n" + WEB_LINE + " Answer in plain words, a few short paragraphs, and nothing else (or the one NEED line, if a screen you were not handed is needed). Do not edit files; search and read, then answer."
    else:
        text += "\n\nTHE QUESTION\n" + question + "\n\nAnswer the question in plain words, a few short paragraphs, and nothing else (or the one NEED line, if a screen you were not handed is needed). Do not run commands, edit files or ask for permissions; answer from the data above, and say plainly when the data does not carry the answer."
    return text


def build_prompt(request, screen, agent_page, history=None):
    """The Build brief for a door: the reader's request to change the desk, with the agent
    page (what the desk is, its folders and addresses) so the app knows the ground."""
    text = BUILD_SYSTEM + "\n\nTHE READER IS ON: " + screen + "\n\nTHE DESK, FOR AN AGENT\n" + agent_page
    turns = [m for m in (history or []) if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)][-6:]
    if turns:
        text += "\n\nTHE CONVERSATION SO FAR\n" + "\n".join(f"{m['role'].upper()}: {m['content']}" for m in turns)
    text += "\n\nTHE REQUEST\n" + request + "\n\nDo it, then answer in plain words: what changed, file by file, and whether the desk needs a restart. Nothing else."
    return text


def ask(question, screen, context, profile="", history=None, s=None, desk_map="", web=False, pictures=None):
    """The Ask box. `context` is the screen's data as text; `history` the last few
    turns as [{'role','content'}]. Returns {'ok', 'answer'} or {'ok': False, 'error'}."""
    system = ASK_SYSTEM + ("\n\n" + WEB_LINE if web else "") + "\n\nSCREEN: " + screen
    if profile:
        system += "\n\nHOW THIS READER INVESTS (from their Settings screen; shape answers to it)\n" + profile
    if desk_map:
        system += "\n\nTHE WHOLE DESK (address, screen, what it holds)\n" + desk_map
    system += "\n\nTHE DATA (this screen first, then the screens the question points at)\n" + context
    messages = [m for m in (history or []) if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)][-6:]
    s = s or settings()
    blocks = []
    for p in (pictures or []):
        # the reader's own chart pictures go in as pictures, each named so the answer can quote it
        b = _image_block(p, s["format"])
        if b:
            blocks.append({"type": "text", "text": f"The reader's picture: {p['title']}" + (f" ({p['period']})" if p.get("period") else "")})
            blocks.append(b)
    if blocks:
        system += "\n\nTHE READER'S PICTURES ON THIS SUBJECT are attached to the question (chart clippings and screenshots they kept in their notes); look at each, and quote it by its title."
        blocks.append({"type": "text", "text": question})
        messages.append({"role": "user", "content": blocks})
    else:
        messages.append({"role": "user", "content": question})
    out = complete(messages, system=system, max_tokens=2000 if web else 1200, timeout=240 if web else 120, s=s, web=web)
    if not out["ok"]:
        return out
    if out.get("refused"):
        return {"ok": True, "answer": "The model declined to answer that one."}
    return {"ok": True, "answer": out["text"] or "(the model sent an empty answer)", "sources": out.get("sources") or []}
