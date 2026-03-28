import type { BacktestMetrics } from '@/lib/types/run'

function isFiniteNumber(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v)
}

/**
 * Parse and validate backtest_metrics report JSON from the API.
 * Returns null if malformed or missing required fields.
 */
export function parseBacktestMetrics(report: string): BacktestMetrics | null {
  let data: unknown
  try {
    data = JSON.parse(report)
  } catch {
    return null
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null
  const r = data as Record<string, unknown>

  if (!isFiniteNumber(r.initial_cash) || !isFiniteNumber(r.final_equity)) return null

  const tr = r.total_return_pct
  const total_return_pct =
    tr === null || tr === undefined
      ? null
      : isFiniteNumber(tr)
        ? tr
        : null

  if (
    !isFiniteNumber(r.unrealized_pnl) ||
    !isFiniteNumber(r.realized_pnl) ||
    !isFiniteNumber(r.total_fees_paid)
  ) {
    return null
  }
  if (typeof r.fill_count !== 'number' || !Number.isInteger(r.fill_count)) return null

  const mdd = r.max_drawdown_pct
  const max_drawdown_pct =
    mdd === null || mdd === undefined
      ? null
      : isFiniteNumber(mdd)
        ? mdd
        : null

  const asOf = r.as_of
  const as_of =
    asOf === null || asOf === undefined
      ? null
      : typeof asOf === 'string'
        ? asOf
        : null

  if (!r.positions || typeof r.positions !== 'object' || Array.isArray(r.positions)) return null
  const positions: Record<string, string> = {}
  for (const [k, v] of Object.entries(r.positions as Record<string, unknown>)) {
    if (typeof v !== 'string') return null
    positions[k] = v
  }

  return {
    initial_cash: r.initial_cash,
    final_equity: r.final_equity,
    total_return_pct,
    unrealized_pnl: r.unrealized_pnl,
    realized_pnl: r.realized_pnl,
    total_fees_paid: r.total_fees_paid,
    fill_count: r.fill_count,
    max_drawdown_pct,
    as_of,
    positions,
  }
}
