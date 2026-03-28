import type { BacktestMetrics } from '@/lib/types/run'

/**
 * Client-side headline when `backtest_headline:0` is missing (older runs).
 * Must stay aligned with server `format_backtest_headline` semantics.
 */
export function deriveBacktestHeadlineFromMetrics(
  ticker: string,
  tradeDate: string,
  endDate: string | null,
  m: BacktestMetrics,
): string {
  const sym = ticker.trim().toUpperCase()
  const rng = endDate && endDate !== tradeDate ? `${tradeDate} → ${endDate}` : tradeDate
  const ret =
    m.total_return_pct === null
      ? 'N/A%'
      : `${m.total_return_pct > 0 ? '+' : ''}${m.total_return_pct.toFixed(2)}%`
  const eq = `$${m.final_equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  return `${sym} · ${rng} · ${m.fill_count} fills · Final ${eq} · ${ret}`
}
