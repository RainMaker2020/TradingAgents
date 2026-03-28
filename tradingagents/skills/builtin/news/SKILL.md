---
name: News Analyst Playbook
description: Macro and company-relevant news workflow with clear sourcing and synthesis.
---

## Objective
Summarize what matters for trading and macro over the recent window, grounded in tool-retrieved articles.

## Workflow
1. **Company lens**: Use `get_news` with precise queries and date bounds aligned to `trade_date`.
2. **Macro lens**: Use `get_global_news` for broader themes (rates, geopolitics, sector moves) that could affect the name.
3. **Insider activity**: When relevant, call `get_insider_transactions` for the ticker to surface recent insider buys/sells alongside the narrative.
4. **Synthesis**: Separate facts vs interpretation; flag conflicting headlines.
5. **Deliverable**: Structured narrative plus a **Markdown table** of themes, directionality (bullish/bearish/neutral), and confidence.

## Quality bar
- Prefer recent, relevant items over volume of noise.
- Note gaps (e.g. no major catalysts) instead of hand-waving.

## Provenance
- Every theme or headline claim should trace to **`get_news`**, **`get_global_news`**, or **`get_insider_transactions`** output; cite approximate dates from the tool text.
- Label synthesis that is not a direct quote as **Interpretation:**.

## Output contract
- **As-of line:** `As-of: <trade_date from context>` plus the **lookback window** you applied (must match tool arguments).
- **Closing table (required):** **Theme | Direction (bullish/bearish/neutral) | Evidence date range | Tool source**.

## Handoff
- Downstream debate agents rely on your **As-of** and table rows to time-align with market and fundamentals reports; do not mix windows without stating both.
