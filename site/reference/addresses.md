---
title: The addresses
nav: Addresses
description: Every page GreekSoup serves and every plain-JSON address behind it, on your own computer, the same list the desk hands an AI agent, all read-only.
lead: The desk answers at one address on your own computer, `http://localhost:8765/` unless you changed the door number, and every screen has a plain-JSON address behind it. This is the list, the same one the desk hands an AI agent at `/agent`. Everything is read-only; nothing here places an order or changes an account.
---

## Pages and what stands behind them

| Page | Screen | JSON behind it |
|---|---|---|
| `/` | Desk · Home and the US panels | `/api/snapshot` the broker book; `/api/usbook` the US book priced; `/api/earnings` the earnings ahead; `/api/insiders` the insider tape; `/api/pulse` the market pulse |
| `/book` | Desk · Book | `/api/book` |
| `/risk` | Risk | `/api/risk` |
| `/watch` | Watch · Home | `/api/watch?list=home`, `/api/results_home` |
| `/watch?list=us` | Watch · US | `/api/watch?list=us` |
| `/watch?list=global` | Global | `/api/watch?list=global` |
| `/funds` | Funds | `/api/funds` the 13F holdings; `/api/activist` the 13D and 13G feed |
| `/flow` | Flow | `/api/flow` |
| `/short` | Short | `/api/short` |
| `/capitol` | Capitol | `/api/capitol` |
| `/calendar` | Calendar | `/api/calendar` |
| `/macro` | Macro | `/api/macro` the cards; `/api/econcal` the economic calendar |
| `/commods` | Commodities | `/api/commods` |
| `/chain` | Chain | `/api/chain` |
| `/notes` | Notes | `/api/notes?symbol=&project=&kind=&period=&about=&type=&q=`; `/api/notes/get?id=`; `/api/notes/graph?symbol=`; `/api/research/tasks`, `/api/research/journal`, `/api/research/timeline?symbol=`, `/api/research/context?symbol=`, `/api/research/status?symbol=`, `/api/research/file?path=`, `/api/research/text?path=`, `/api/research/block?spec=` |
| `/t?symbol=X` | A ticker page | the ticker page's own reads |
| `/settings` | Settings | `/api/settings`, `/api/nav`, `/api/update`, `/api/doctor` |
| `/report` | Tell us | `/api/report/list` |
| `/agent` | The page for an AI agent | the same list as this page, as plain text, with the file shapes |

## Who can reach them

Only this computer. Every request must name it as its host, and a request from a browser must come from the desk's own pages; anything else is refused before it is read. That is what lets the desk run with no login. [Security](/docs/project/security/) explains both guards, and [Your computer or a server](/docs/install/your-computer-or-a-server/) says why a server turns the story around.

## For an agent

Open `/agent` in a browser, or hand its text to your AI: it lists every address above with the shape of each answer, the research vault's file layout, and the rule that every figure names its source on the screen it came from. [Your AI](/docs/setup/your-ai/#the-page-your-ai-app-reads).
