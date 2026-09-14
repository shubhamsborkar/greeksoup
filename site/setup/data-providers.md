---
title: Data providers
nav: Data providers
description: What a data provider key adds to GreekSoup, the one that ships (Financial Modeling Prep), and how any other provider is one file to a written contract.
lead: The desk runs without one. A data key adds the parsed financials and a few columns; another provider is one file your agent writes.
---

## What a key adds

With no key, the ticker page carries the chart, the quote, the ratios and the insider table from the public record. A data key adds, on top:

- six years of statements, the ratio history, segments, estimates, peers, dividends and news on the ticker page, and a DCF sandbox;
- the 50 and 200 day columns on the US watch grid;
- a market-wide insider scan, and cleaner rows on Capitol.

## The one that ships

Financial Modeling Prep. Paste the key in Settings under **Data provider** and click *Check what it allows*: the desk runs each endpoint it uses against your plan and shows which answered, so you know before a screen does. The desk was built on the Starter plan.

## Another provider

Any provider that serves the same kinds of data is one file in the `data_providers` folder, written to the contract in `data_providers/CONTRACT.md`: sixteen functions (quote, profile, the three statements, ratios, estimates, segments, peers, dividends, news, history, latest insiders, Senate trades, float, search), each returning the documented shape or nothing. Open the folder in your agent and say:

```
Read data_providers/CONTRACT.md. Write a provider file for <provider name> to that contract using its API documentation at <link>, reading the key from DATA_API_KEY and the address from DATA_BASE_URL. Then set DATA_PROVIDER to the file's name in Settings and check what it allows.
```

Provider data is subject to the provider's terms. A paid feed's data may not be redistributed, and the desk does not.
