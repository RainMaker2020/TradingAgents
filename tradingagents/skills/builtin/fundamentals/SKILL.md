---
name: Fundamentals Analyst Playbook
description: Financial statements and company profile workflow for a full fundamental picture.
---

## Objective
Build a fundamentals memo suitable for a PM: profitability, balance sheet health, cash generation, and notable filings/events.

## Workflow
1. **Overview**: Start with `get_fundamentals` for context and key metrics.
2. **Statements**: Pull `get_income_statement`, `get_balance_sheet`, and `get_cashflow` as needed for the question implied by the ticker/date.
3. **Narrative**: Connect lines across statements (e.g. margin + working capital + capex).
4. **Deliverable**: Deep report with a closing **Markdown table** of metrics, YoY or trend notes, and risks.

## Quality bar
- Call out accounting quality flags (one-offs, restructuring, dilution) when visible.
- Avoid duplicate tables; one tight summary table beats many raw dumps.

## Provenance
- Each metric or ratio must name the tool that produced it (`get_fundamentals`, `get_income_statement`, etc.) and the fiscal period if shown in the tool output.
- Forward-looking statements from management narratives → mark **Interpretation / forward-looking:**.

## Output contract
- **As-of line:** `As-of: <trade_date from context>` plus fiscal period coverage of the statements you used (e.g. TTM, FY2024).
- **Closing table (required):** **Metric | Value | Period / as-of | Tool source**.

## Handoff
- Research Manager and Risk Judge will compare your **period labels** with market/news timing; mismatched periods must be called out in prose.
