---
title: "Example: a dashboard"
kind: stock
type: general
symbols: [AAPL, MSFT]
about: ""
period: ""
file: ""
project: "How notes connect"
tags: [example]
pinned: false
created: 2026-09-15 12:00
updated: 2026-09-15 12:00
---
A note can carry the desk's live numbers next to your words. Each block below is three backticks, the word desk, one line naming the block, and three backticks to close; the desk draws it here and any editor shows it as code. A note that is mostly blocks is a dashboard.

```desk
quote AAPL MSFT
```

The two names in the example project, with the day's move. Below, one year of $AAPL as a line, and where it stands in your research.

```desk
chart AAPL 1y
```

```desk
status AAPL
```

The blocks the desk knows: quote, chart, watch (symbols, or a project by title), commodity, status, notes, tasks, timeline, book. The Blocks row under the editor drops one in. Replace this note with your own.
