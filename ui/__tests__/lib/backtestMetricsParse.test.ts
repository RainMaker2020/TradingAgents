import { parseBacktestMetrics } from '@/lib/backtestMetricsParse'

const validJson = JSON.stringify({
  initial_cash: 100000,
  final_equity: 96500,
  total_return_pct: -3.5,
  unrealized_pnl: 1500,
  realized_pnl: 200,
  total_fees_paid: 5,
  fill_count: 2,
  max_drawdown_pct: null,
  as_of: '2024-01-02T00:00:00+00:00',
  positions: { AAPL: '10' },
})

test('parseBacktestMetrics returns typed object for valid API JSON', () => {
  const m = parseBacktestMetrics(validJson)
  expect(m).not.toBeNull()
  expect(m!.final_equity).toBe(96500)
  expect(m!.total_return_pct).toBe(-3.5)
  expect(m!.positions.AAPL).toBe('10')
})

test('parseBacktestMetrics accepts null total_return_pct', () => {
  const raw = JSON.stringify({
    ...JSON.parse(validJson),
    total_return_pct: null,
  })
  const m = parseBacktestMetrics(raw)
  expect(m).not.toBeNull()
  expect(m!.total_return_pct).toBeNull()
})

test('parseBacktestMetrics returns null for invalid JSON', () => {
  expect(parseBacktestMetrics('not json')).toBeNull()
})

test('parseBacktestMetrics returns null when required number missing', () => {
  const bad = JSON.stringify({ ...JSON.parse(validJson), fill_count: 1.5 })
  expect(parseBacktestMetrics(bad)).toBeNull()
})
