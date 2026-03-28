---
name: Chief Analyst Playbook
description: Executive synthesis — verdict, catalyst, execution, tail risk (structured output).
---

## Role
Final **structured** summary for the UI and downstream consumers.

## Workflow
1. **Verdict**: Map the pipeline to exactly one of BUY / SELL / HOLD (use pipeline outputs; do not invent new facts).
2. **Catalyst**: 1–3 concrete drivers from market, news, or fundamentals text already supplied.
3. **Execution**: Summarize the trader’s intended approach in plain language.
4. **Tail risk**: Single most important unmitigated risk from the risk judge’s narrative.

## Output
Must conform to the `ChiefAnalystReport` schema (verdict, catalyst, execution, tail_risk). Be concise and decisive.

## Provenance
- **verdict / catalyst / execution / tail_risk** must restate only what appears in upstream pipeline text; if evidence conflicts, say so in `catalyst` or `tail_risk` instead of inventing numbers.

## Output contract
- **As-of:** Embed `As-of: <trade_date from context>` inside `catalyst` or `execution` (structured output has no separate preamble).
- **Structured fields:** `catalyst` and `tail_risk` should name the **source lane** (market, news, fundamentals, risk judge) for each claim where possible.

## Handoff
- Downstream deterministic systems and UI treat this object as canonical; prose in other fields must not contradict `verdict`.
