---
title: Your AI
nav: Your AI
description: How an AI reads GreekSoup: the page made for any AI app on your computer, and your own key with fourteen presets, models on your own computer among them.
lead: Two ways in. The Ask box on every screen sends your question with that screen's numbers to your own key. And any AI app on your computer can read the whole desk through one page, so it answers about your book and not about a stranger's.
---

## The Ask box

Click **Ask · your AI** at the bottom of the sidebar, or press ⌘I (Ctrl+I on Windows and Linux). A box opens on the right of whichever screen you are on. Type a question and press Enter. The question goes to the AI you set in Settings together with that screen's own numbers, the same numbers the screen is showing you, and the answer comes back in the box with a line saying which addresses it read. The box remembers the conversation while the screen is open, so a second question can build on the first.

What it sends: your question, the screen's numbers, and the "how you invest" lines from Settings if you filled them in, so the answer fits you. Where it sends them: to the one address you chose under Your AI, and nowhere else. A model running on your computer through Ollama or LM Studio never leaves it.

What it does not do: it does not tell you what to buy, sell or hold, and it is told to say so when a question is not answered by the screen's numbers rather than guess. Every figure it quotes should match the screen and the source the screen names; check it there before acting on anything.

## The page your AI app reads

The desk carries a page written for an AI agent. It lists every screen and the address that returns its numbers, says that everything is read-only, tells the agent not to read your settings file, and carries how you invest, from the **How you invest** section of Settings, so the answers fit you.

Open Settings, find **Connect your AI app**, and click Copy. Then, in whichever AI app you use:

- **Claude Code, Codex, Kimi Code, Grok Build**, or any agent that works in a folder: open the desk folder and say "read the agent page at that address, then answer my questions about my book from it." The README in the folder says the same thing to the agent.
- **A chat app on your computer** that can open a local address: paste the address and ask.

The agent reads the desk the way you do, screen by screen, and every number it quotes comes with the source the screen names.

## Your own key

Under **Your AI** in Settings you can pick a provider, paste a key, choose the model and click *Test it*, which sends one small request and shows what came back. Fourteen presets:

Anthropic · OpenAI · Google (Gemini) · DeepSeek · Kimi (Moonshot) · MiniMax · Z.ai (GLM) · Alibaba (Qwen) · xAI (Grok) · Mistral · OpenRouter (many models, one key) · Ollama on this computer · LM Studio on this computer · Any other endpoint.

The two on your computer need no key. *Any other endpoint* takes an address, the request shape it speaks (OpenAI chat or Anthropic messages) and a model name, so a provider not on the list still works.

The key lives in your settings file with your other keys and goes only to the address you chose. The Ask box is what reads it.

## Two agents at once

The page does not care which app reads it, or how many. A reader who uses one agent to build the desk and another to talk about the book points both at the same address.
