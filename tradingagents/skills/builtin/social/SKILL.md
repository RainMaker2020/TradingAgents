---
name: Social & Sentiment Playbook
description: Company-specific sentiment and social/news tone for the trading horizon.
---

## Objective
Characterize how the name is discussed publicly: sentiment trajectory, narratives, and company-specific news that could move the tape.

## Workflow
1. **Search breadth**: Use `get_news` with varied queries (company name, ticker, product lines, CEO/events).
2. **Sentiment**: Infer tone and persistence (spike vs sustained) from what you retrieve — do not invent platforms you did not observe.
3. **Link to price**: Where possible, relate narratives to likely volatility or event risk.
4. **Deliverable**: Long-form analysis plus a **Markdown table** of themes, sentiment, and implications.

## Quality bar
- Separate organic discussion from obvious PR repetition.
- State uncertainty when sources are thin or contradictory.

## Provenance
- Sentiment and narrative claims must come from **`get_news`** retrieval text; if you infer tone, tag **Interpretation:**.
- Do not cite platforms or handles you did not see in tool output.

## Output contract
- **As-of line:** `As-of: <trade_date from context>` plus search window used in `get_news`.
- **Closing table (required):** **Theme / narrative | Sentiment (supporting) | Date range covered | Tool source**.

## Handoff
- Pair your **As-of** with the News Analyst’s macro window when downstream compares social vs headline risk.
