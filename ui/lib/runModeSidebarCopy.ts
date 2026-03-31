/**
 * Shared sidebar copy for New Run vs Run Detail so Graph (LLM) / Backtest (Engine)
 * guidance stays in one place.
 */

export const EXECUTION_FLOW_GRAPH: string[] = [
  'Analysts ingest market, news, fundamentals, and social signals.',
  'Research agents run bull/bear synthesis and manager consensus.',
  'Trader and risk committee process position and risk posture.',
  'Chief analyst publishes final BUY/SELL/HOLD verdict.',
]

export const EXECUTION_FLOW_BACKTEST: string[] = [
  'Engine loads cached OHLCV (Yahoo-style CSV) for the symbol.',
  'Each calendar day in range is stepped; LangGraph may run per bar for signals (signal cache applies).',
  'Risk checks and simulated execution (next-bar open, slippage, fees) update portfolio state.',
  'Run completes with metrics, simulation trace, and summary (including data file + loaded bar range).',
]

/** Pre-launch — New Run sidebar */
export const OPERATOR_GUIDANCE_PRE_GRAPH: string[] = [
  'Confirm ticker and trade date match the session you want the LLM graph to analyze.',
  'Use a higher-capacity deep model when the symbol or thesis is complex.',
  'Increase debate rounds only when you expect genuine bull/bear conflict.',
  'Keep social analyst enabled when narrative or momentum matters for the name.',
]

export const OPERATOR_GUIDANCE_PRE_BACKTEST: string[] = [
  'Confirm start and end dates define the exact backtest window; end date is required.',
  'Ensure your data cache covers that window (otherwise expect DATA_SKIPPED days in the trace).',
  'Tune simulation config—cash, slippage, fees, max position—before launch; engine uses these directly.',
  'LLM choice still affects LangGraph signals per bar; cache hits reduce token usage.',
]

/** Post-run — Run detail sidebar (aligned themes with pre-launch; adds run-specific actions) */
export const OPERATOR_GUIDANCE_POST_GRAPH: string[] = [
  'Confirm ticker and session date still match what the LLM graph analyzed.',
  'Wait for all pipeline steps to finish before relying on the verdict banner.',
  'Use Diagnostics to inspect per-agent token usage and slow stages.',
  'Escalate if any step remains in running state abnormally long.',
  'Read phase reports alongside the final BUY/SELL/HOLD before any real-world action.',
]

export const OPERATOR_GUIDANCE_POST_BACKTEST: string[] = [
  'Cross-check start/end dates with the backtest window and with “Loaded bars” in the full engine output.',
  'Ensure you had cache coverage for that range (DATA_SKIPPED in the trace means a missing bar day).',
  'Review fills, final equity, exposure, max drawdown, and fees against the simulation config you launched with.',
  'Wait for engine summary and metrics before treating the run as final; use Abort only if the engine hangs.',
  'Export JSON for offline review of metrics and the simulation trace.',
]
