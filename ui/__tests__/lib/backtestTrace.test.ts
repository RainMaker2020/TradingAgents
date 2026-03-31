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

test('summarizeBacktestEvent highlights engine stop-loss / take-profit exits', () => {
  const stop: BacktestTraceEvent = {
    event_type: 'SIGNAL_GENERATED',
    detail: 'risk_forced_exit:stop_loss',
    signal: {
      direction: 'SELL',
      reasoning: 'risk: stop_loss (close 94 <= floor 95)',
    },
  }
  expect(summarizeBacktestEvent(stop)).toMatch(/Stop-loss \(engine\)/)
  expect(summarizeBacktestEvent(stop)).toMatch(/SELL/)

  const tp: BacktestTraceEvent = {
    event_type: 'SIGNAL_GENERATED',
    detail: 'risk_forced_exit:take_profit',
    signal: { direction: 'SELL', reasoning: 'risk: take_profit' },
  }
  expect(summarizeBacktestEvent(tp)).toMatch(/Take-profit \(engine\)/)
})
