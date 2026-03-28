import { deriveBacktestHeadlineFromMetrics } from '@/lib/backtestHeadline'
import type { BacktestMetrics } from '@/lib/types/run'

const base: BacktestMetrics = {
  initial_cash: 100000,
  final_equity: 96500,
  total_return_pct: -3.5,
  unrealized_pnl: 0,
  realized_pnl: 0,
  total_fees_paid: 1.25,
  fill_count: 2,
  max_drawdown_pct: null,
  as_of: null,
  positions: {},
}

test('deriveBacktestHeadlineFromMetrics matches server-style pattern', () => {
  const h = deriveBacktestHeadlineFromMetrics('msft', '2024-01-02', '2024-01-05', base)
  expect(h).toMatch(/MSFT/)
  expect(h).toMatch(/2024-01-02 → 2024-01-05/)
  expect(h).toMatch(/2 fills/)
  expect(h).toMatch(/-3\.50%/)
})

test('deriveBacktestHeadlineFromMetrics single date when end equals start', () => {
  const h = deriveBacktestHeadlineFromMetrics('aapl', '2024-06-01', '2024-06-01', base)
  expect(h).toContain('2024-06-01')
  expect(h).not.toContain('→')
})

test('deriveBacktestHeadlineFromMetrics N/A when total_return_pct null', () => {
  const h = deriveBacktestHeadlineFromMetrics('x', '2024-01-01', null, {
    ...base,
    total_return_pct: null,
  })
  expect(h).toContain('N/A%')
})
