---
title: Your AI
nav: Your AI
description: Three ways to have an AI on the GreekSoup desk: an app you already pay for (Claude Code, Codex, Gemini CLI, Kimi Code, Grok Build, Qwen Code, Cursor) without a key, your own key from any of fourteen labs, or a model running on your own computer. What the Ask box sends, and what the desk never sees.
lead: Three ways in, and the first needs no key at all. An app you already pay for on this computer, a key from a lab, or a model running on your own computer. The Ask box on every screen, the chain draft and every answer on the desk go through whichever you pick.
---

## An app you already pay for

Settings, under **Your AI**, opens with the apps the desk finds on this computer: Claude Code on a Claude subscription, Codex on a ChatGPT subscription, Gemini CLI on a Google account, Kimi Code, Grok Build, Qwen Code and Cursor on their own accounts. Each card says whether the app is on this computer, and carries two buttons.

**Use it for Ask** makes that app the one who answers. From then on every question in the Ask box, and every chain draft, goes to it. The desk hands the app your question with the screen's numbers on standard input and reads the answer from standard output, exactly as you would at a terminal. If the Terminal door that carries this is not in yet, the button brings it in for you.

**Sign in** opens a terminal window running the app's own sign-in, which continues in your browser. The desk never sees the login: the app keeps its own, reaches its own provider under your own account, and that is the one thing it talks to. When the window says you are in, close it and come back.

The brief the desk gives the app says: answer from the data, run no commands, edit no files, ask for no permissions. The app's own permission settings apply on top, and reading them once is worth the minute.

An app that is not on this computer shows a link to get it. Once it is installed, reopen Settings and the card finds it.

## Is this allowed by the app's maker, and is my account safe

A fair question, because in 2026 Anthropic cut off other programs that took a Claude subscription's login token and used it to reach Claude directly. The desk does not do that. It never sees a token: it runs the maker's own app on your computer, the way a shell script would, hands it a question and reads the answer. That is the app being used as the app, under your own sign-in, and each maker documents this way of running it (Claude Code's print mode, Codex's `exec`, Gemini CLI's `-p`, and the same flag on Kimi Code, Grok Build, Qwen Code and Cursor). Nothing about your desk is shared with anyone else, and nobody else's questions go through your account.

What the maker's rules do govern is how the usage is counted. As of 15 June 2026 Anthropic says questions through Claude Code's print mode still draw from your subscription's usage limits, and that it has paused a plan to move them to a separate monthly credit; if that plan returns, the Ask box would count against that credit instead, and the desk's Settings page will say so. OpenAI documents `codex exec` for scripts on a ChatGPT plan and recommends an API key for heavy automation. Google's Gemini CLI runs on a Google account. If a maker changes its rules, the rules win: switch the Ask box to a key from a lab, or to a model running on your computer, and nothing else on the desk changes.

## A key from a lab

Under the apps, pick a provider, paste a key, choose the model and click *Test it*, which sends one small line and shows what came back. Fourteen presets:

Anthropic · OpenAI · Google (Gemini) · DeepSeek · Kimi (Moonshot) · MiniMax · Z.ai (GLM) · Alibaba (Qwen) · xAI (Grok) · Mistral · OpenRouter (many models, one key) · Ollama on this computer · LM Studio on this computer · Any other endpoint.

*Any other endpoint* takes the address where it answers, how it is spoken to (the common way most labs and every local model speak, or Anthropic's own) and a model name, so a provider not on the list still works. The key lives in your settings file with your other keys and goes only to the address you chose.

## A model on this computer

Ollama and LM Studio are two of the presets and need no key. A question to one of them never leaves your computer. Pick the preset, type the model's name as the app lists it, and test it.

## The Ask box

Click **Ask · your AI** at the bottom of the sidebar, or press ⌘I (Ctrl+I on Windows and Linux). A box opens on the right of whichever screen you are on. Type a question and press Enter. The question goes to the AI you chose together with that screen's own numbers, the same numbers the screen is showing you, and the answer comes back in the box with a line saying which addresses it read. The box remembers the conversation while the screen is open, so a second question can build on the first.

A picker at the top of the box names who answers: the app you chose, or the key on Settings. It can be changed for one question.

What it sends: your question, the screen's numbers, and the "how you invest" lines from Settings if you filled them in, so the answer fits you. On Desk · Home the screen's numbers are your book, which is the point of asking and a fact to know. Where it sends them: to the one place you chose, and nowhere else.

What it does not do: it does not tell you what to buy, sell or hold, and it is told to say so when a question is not answered by the screen's numbers rather than guess. Every figure it quotes should match the screen and the source the screen names; check it there before acting on anything.

An answer worth keeping has **Save as note** and **Save as task** under it. Nothing is saved until you press one.

## Where else the AI works

- **Chain**: describe an industry, a product or a company and **Draft it** fills the map, upstream to downstream, for you to keep, change or drop line by line. [Chains](/docs/setup/chains/).
- **The ⋯ on any name**: *Ask your AI about it* opens the box with the name already in the question.

## The page your AI app reads

The desk also carries a page written for any AI agent on your computer. It lists every screen and the address that returns its numbers, says that everything is read-only, tells the agent not to read your settings file, and carries how you invest, so the answers fit you. Settings, under **Connect your AI app**, has the address and a Copy button. Open the desk folder in Claude Code, Codex, Kimi Code, Grok Build or whichever you use, and say "read the agent page at that address, then answer my questions about my book from it." The page does not care which app reads it, or how many.
