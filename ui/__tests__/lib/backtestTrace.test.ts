import { normalizeBacktestTrace, summarizeBacktestEvent } from '@/lib/backtestTrace'
import type { BacktestTraceEvent } from '@/lib/types/run'

test('normalizeBacktestTrace drops invalid rows', () => {
  expect(normalizeBacktestTrace(null)).toEqual([])
  expect(normalizeBacktestTrace([1, 'x', { event_type: 'X' }])).toHaveLength(1)
})

test('summarizeBacktestEvent prefers rejection then signal then fill', () => {
  const rej: BacktestTraceEvent = {
    event_type: 'SIGNAL_REJECTED',
    rejection: { code: 'STRATEGY_TIMEOUT', detail: 'cancelled' },
  }
  expect(summarizeBacktestEvent(rej)).toContain('STRATEGY_TIMEOUT')

  const sig: BacktestTraceEvent = {
    event_type: 'SIGNAL_GENERATED',
    signal: { direction: 'BUY', reasoning: 'Momentum' },
  }
  expect(summarizeBacktestEvent(sig)).toContain('BUY')

  const fill: BacktestTraceEvent = {
    event_type: 'FILL_EXECUTED',
    fill: { direction: 'BUY', filled_quantity: '10', fill_price: '100', fees: '1' },
  }
  expect(summarizeBacktestEvent(fill)).toMatch(/BUY/)
  expect(summarizeBacktestEvent(fill)).toMatch(/100/)
})
