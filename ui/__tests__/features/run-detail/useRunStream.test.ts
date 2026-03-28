import { renderHook, act } from '@testing-library/react'
import { useRunStream } from '@/features/run-detail/hooks/useRunStream'

jest.mock('@/lib/sse', () => ({
  createSSEConnection: jest.fn((url: string, handlers: Record<string, (d: unknown) => void>) => {
    setTimeout(() => {
      // First turn of bull_researcher
      handlers.onAgentStart?.({ step: 'bull_researcher', turn: 0 })
      handlers.onAgentComplete?.({ step: 'bull_researcher', turn: 0, report: 'Bull case round 1' })
      // Second turn of bull_researcher
      handlers.onAgentStart?.({ step: 'bull_researcher', turn: 1 })
      handlers.onAgentComplete?.({ step: 'bull_researcher', turn: 1, report: 'Bull case round 2' })
      handlers.onRunComplete?.({ decision: 'BUY', run_id: 'abc' })
    }, 0)
    return jest.fn()
  }),
}))

// getRun defaults to 'queued' so existing SSE-path tests still exercise the SSE branch.
// Tests that need a different status use mockResolvedValueOnce to override.
jest.mock('@/lib/api-client', () => ({
  getRunStreamUrl: (id: string) => `/api/runs/${id}/stream`,
  getRun: jest.fn().mockResolvedValue({
    id: 'abc',
    ticker: 'NVDA',
    date: '2026-03-23',
    status: 'queued',
    decision: null,
    created_at: '2026-03-23T00:00:00Z',
    config: null,
    reports: {},
    error: null,
  }),
  abortRun: jest.fn().mockResolvedValue({ status: 'aborted' }),
}))

test('appends multiple turns for same step', async () => {
  const { result } = renderHook(() => useRunStream('abc'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })
  expect(result.current.reports['bull_researcher']).toEqual([
    'Bull case round 1',
    'Bull case round 2',
  ])
})

test('step status stays done after multiple turns', async () => {
  const { result } = renderHook(() => useRunStream('abc'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })
  expect(result.current.steps['bull_researcher']).toBe('done')
})

test('verdict and status set on run:complete', async () => {
  const { result } = renderHook(() => useRunStream('abc'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })
  expect(result.current.verdict).toBe('BUY')
  expect(result.current.status).toBe('complete')
})

test('initial reports are empty arrays', () => {
  const { result } = renderHook(() => useRunStream('abc'))
  expect(result.current.reports['market_analyst']).toEqual([])
})

test('hydrates from reports when run is complete, skipping SSE', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')

  // Reset call history so we can assert createSSEConnection was NOT called for this run
  jest.clearAllMocks()

  getRun.mockResolvedValueOnce({
    id: 'xyz',
    ticker: 'AAPL',
    date: '2026-03-23',
    status: 'complete',
    decision: 'SELL',
    created_at: '2026-03-23T00:00:00Z',
    config: null,
    reports: { 'market_analyst:0': 'bearish signal' },
    error: null,
  })

  const { result } = renderHook(() => useRunStream('xyz'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(result.current.status).toBe('complete')
  expect(result.current.verdict).toBe('SELL')
  expect(result.current.reports['market_analyst']).toEqual(['bearish signal'])
  expect(createSSEConnection).not.toHaveBeenCalled()  // SSE skipped for completed run
})

test('hydrates backtest_summary report separately from agent steps', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')
  jest.clearAllMocks()

  getRun.mockResolvedValueOnce({
    id: 'bt1',
    ticker: 'AAPL',
    date: '2024-01-02',
    status: 'complete',
    decision: 'HOLD',
    created_at: '2024-01-02T00:00:00Z',
    config: {
      mode: 'backtest',
      end_date: '2024-01-10',
      llm_provider: 'deepseek',
      deep_think_llm: 'deepseek-reasoner',
      quick_think_llm: 'deepseek-chat',
    },
    reports: { 'backtest_summary:0': 'Backtest: AAPL 2024-01-02 -> 2024-01-10' },
    error: null,
    token_usage: {},
  })

  const { result } = renderHook(() => useRunStream('bt1'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(createSSEConnection).not.toHaveBeenCalled()
  expect(result.current.mode).toBe('backtest')
  expect(result.current.endDate).toBe('2024-01-10')
  expect(result.current.llmProvider).toBe('deepseek')
  expect(result.current.deepThinkLlm).toBe('deepseek-reasoner')
  expect(result.current.quickThinkLlm).toBe('deepseek-chat')
  expect(result.current.backtestSummary).toContain('Backtest: AAPL')
  expect(result.current.reports['market_analyst']).toEqual([])
})

test('hydrates backtest_headline and backtest_metrics on completed backtest', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')
  jest.clearAllMocks()

  const metricsJson = JSON.stringify({
    initial_cash: 100000,
    final_equity: 96500,
    total_return_pct: -3.5,
    unrealized_pnl: 0,
    realized_pnl: 0,
    total_fees_paid: 0,
    fill_count: 2,
    max_drawdown_pct: null,
    as_of: null,
    positions: {},
  })

  getRun.mockResolvedValueOnce({
    id: 'bt2',
    ticker: 'MSFT',
    date: '2024-01-02',
    status: 'complete',
    decision: 'HOLD',
    created_at: '2024-01-02T00:00:00Z',
    config: { mode: 'backtest', end_date: '2024-01-05' },
    reports: {
      'backtest_headline:0': 'MSFT · 2024-01-02 → 2024-01-05 · 2 fills · Final $96,500.00 · -3.50%',
      'backtest_metrics:0': metricsJson,
      'backtest_summary:0': 'full dump',
    },
    error: null,
    token_usage: {},
  })

  const { result } = renderHook(() => useRunStream('bt2'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(createSSEConnection).not.toHaveBeenCalled()
  expect(result.current.backtestHeadline).toContain('MSFT')
  expect(result.current.backtestHeadline).toContain('fills')
  expect(result.current.backtestMetrics?.final_equity).toBe(96500)
  expect(result.current.backtestSummary).toBe('full dump')
})

test('hydrates backtest_trace on completed backtest', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')
  jest.clearAllMocks()

  getRun.mockResolvedValueOnce({
    id: 'bt3',
    ticker: 'MSFT',
    date: '2024-01-02',
    status: 'complete',
    decision: 'HOLD',
    created_at: '2024-01-02T00:00:00Z',
    config: { mode: 'backtest', end_date: '2024-01-05' },
    reports: { 'backtest_summary:0': 'summary' },
    error: null,
    token_usage: {},
    backtest_trace: [
      {
        event_type: 'SIGNAL_GENERATED',
        timestamp: '2024-01-02T21:00:00+00:00',
        symbol: 'MSFT',
        signal: { direction: 'HOLD', reasoning: 'No edge' },
      },
    ],
  })

  const { result } = renderHook(() => useRunStream('bt3'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(createSSEConnection).not.toHaveBeenCalled()
  expect(result.current.backtestTrace).toHaveLength(1)
  expect(result.current.backtestTrace?.[0].event_type).toBe('SIGNAL_GENERATED')
  expect(result.current.backtestTrace?.[0].signal?.direction).toBe('HOLD')
})

test('AGENT_COMPLETE accumulates tokensByStep and tokensTotal', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')
  jest.clearAllMocks()

  // getRun returns queued so SSE path runs
  getRun.mockResolvedValueOnce({
    id: 'abc', ticker: 'NVDA', date: '2026-03-23', status: 'queued',
    decision: null, created_at: '2026-03-23T00:00:00Z',
    config: null, reports: {}, error: null, token_usage: null,
  })

  // SSE mock emits one agent:complete with token data
  createSSEConnection.mockImplementationOnce(
    (_url: string, handlers: Record<string, (d: unknown) => void>) => {
      setTimeout(() => {
        handlers.onAgentStart?.({ step: 'market_analyst', turn: 0 })
        handlers.onAgentComplete?.({
          step: 'market_analyst', turn: 0, report: 'bullish',
          tokens_in: 1200, tokens_out: 400,
        })
        handlers.onRunComplete?.({ decision: 'BUY', run_id: 'abc' })
      }, 0)
      return jest.fn()
    }
  )

  const { result } = renderHook(() => useRunStream('abc'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(result.current.tokensByStep['market_analyst']).toEqual({ in: 1200, out: 400 })
  expect(result.current.tokensTotal).toEqual({ in: 1200, out: 400 })
})

test('missing tokens_in/out in AGENT_COMPLETE defaults to 0', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')
  jest.clearAllMocks()

  getRun.mockResolvedValueOnce({
    id: 'abc', ticker: 'NVDA', date: '2026-03-23', status: 'queued',
    decision: null, created_at: '2026-03-23T00:00:00Z',
    config: null, reports: {}, error: null, token_usage: null,
  })

  createSSEConnection.mockImplementationOnce(
    (_url: string, handlers: Record<string, (d: unknown) => void>) => {
      setTimeout(() => {
        handlers.onAgentStart?.({ step: 'news_analyst', turn: 0 })
        // No tokens_in/tokens_out in payload
        handlers.onAgentComplete?.({ step: 'news_analyst', turn: 0, report: 'ok' })
        handlers.onRunComplete?.({ decision: 'HOLD', run_id: 'abc' })
      }, 0)
      return jest.fn()
    }
  )

  const { result } = renderHook(() => useRunStream('abc'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(result.current.tokensByStep['news_analyst']).toEqual({ in: 0, out: 0 })
  expect(result.current.tokensTotal).toEqual({ in: 0, out: 0 })
})

test('duplicate AGENT_COMPLETE for same turn is ignored', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')
  jest.clearAllMocks()

  getRun.mockResolvedValueOnce({
    id: 'dup1', ticker: 'AAPL', date: '2026-03-23', status: 'queued',
    decision: null, created_at: '2026-03-23T00:00:00Z',
    config: null, reports: {}, error: null, token_usage: null,
  })

  createSSEConnection.mockImplementationOnce(
    (_url: string, handlers: Record<string, (d: unknown) => void>) => {
      setTimeout(() => {
        handlers.onAgentStart?.({ step: 'market_analyst', turn: 0 })
        handlers.onAgentComplete?.({
          step: 'market_analyst', turn: 0, report: 'same report',
          tokens_in: 100, tokens_out: 50,
        })
        // Replay/duplicate event for same step + turn
        handlers.onAgentComplete?.({
          step: 'market_analyst', turn: 0, report: 'same report',
          tokens_in: 100, tokens_out: 50,
        })
        handlers.onRunComplete?.({ decision: 'HOLD', run_id: 'dup1' })
      }, 0)
      return jest.fn()
    }
  )

  const { result } = renderHook(() => useRunStream('dup1'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(result.current.reports['market_analyst']).toEqual(['same report'])
  expect(result.current.tokensByStep['market_analyst']).toEqual({ in: 100, out: 50 })
  expect(result.current.tokensTotal).toEqual({ in: 100, out: 50 })
})

test('completed-run hydration populates tokens from getRun().token_usage without SSE', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')
  jest.clearAllMocks()

  getRun.mockResolvedValueOnce({
    id: 'tok', ticker: 'AAPL', date: '2026-03-23', status: 'complete',
    decision: 'BUY', created_at: '2026-03-23T00:00:00Z',
    config: null,
    reports: { 'market_analyst:0': 'bullish' },
    error: null,
    token_usage: { 'market_analyst:0': { tokens_in: 1200, tokens_out: 400 } },
  })

  const { result } = renderHook(() => useRunStream('tok'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(createSSEConnection).not.toHaveBeenCalled()
  expect(result.current.status).toBe('complete')
  expect(result.current.tokensByStep['market_analyst']).toEqual({ in: 1200, out: 400 })
  expect(result.current.tokensTotal).toEqual({ in: 1200, out: 400 })
})

test('AGENT_COMPLETE for chief_analyst parses JSON into chiefAnalystReport', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')
  jest.clearAllMocks()

  getRun.mockResolvedValueOnce({
    id: 'ca1', ticker: 'AAPL', date: '2024-01-15', status: 'queued',
    decision: null, created_at: '2024-01-15T00:00:00Z',
    config: null, reports: {}, error: null, token_usage: null,
  })

  const reportPayload = JSON.stringify({
    verdict: 'BUY',
    catalyst: 'Strong Q4 earnings',
    execution: 'Enter at market, SL at 180',
    tail_risk: 'Rate hike risk',
  })

  createSSEConnection.mockImplementationOnce(
    (_url: string, handlers: Record<string, (d: unknown) => void>) => {
      setTimeout(() => {
        handlers.onAgentStart?.({ step: 'chief_analyst', turn: 0 })
        handlers.onAgentComplete?.({ step: 'chief_analyst', turn: 0, report: reportPayload })
        handlers.onRunComplete?.({ decision: 'BUY', run_id: 'ca1' })
      }, 0)
      return jest.fn()
    }
  )

  const { result } = renderHook(() => useRunStream('ca1'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(result.current.chiefAnalystReport).toEqual({
    verdict: 'BUY',
    catalyst: 'Strong Q4 earnings',
    execution: 'Enter at market, SL at 180',
    tail_risk: 'Rate hike risk',
  })
  // Raw JSON must also land in reports['chief_analyst']
  expect(result.current.reports['chief_analyst']).toEqual([reportPayload])
})

test('AGENT_COMPLETE for chief_analyst with invalid JSON sets chiefAnalystReport to null', async () => {
  const { getRun } = jest.requireMock('@/lib/api-client')
  const { createSSEConnection } = jest.requireMock('@/lib/sse')
  jest.clearAllMocks()

  getRun.mockResolvedValueOnce({
    id: 'ca2', ticker: 'AAPL', date: '2024-01-15', status: 'queued',
    decision: null, created_at: '2024-01-15T00:00:00Z',
    config: null, reports: {}, error: null, token_usage: null,
  })

  createSSEConnection.mockImplementationOnce(
    (_url: string, handlers: Record<string, (d: unknown) => void>) => {
      setTimeout(() => {
        handlers.onAgentStart?.({ step: 'chief_analyst', turn: 0 })
        handlers.onAgentComplete?.({ step: 'chief_analyst', turn: 0, report: 'not-valid-json' })
        handlers.onRunComplete?.({ decision: 'HOLD', run_id: 'ca2' })
      }, 0)
      return jest.fn()
    }
  )

  const { result } = renderHook(() => useRunStream('ca2'))
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

  expect(result.current.chiefAnalystReport).toBeNull()
})

test('initial chiefAnalystReport is null', () => {
  const { result } = renderHook(() => useRunStream('abc'))
  expect(result.current.chiefAnalystReport).toBeNull()
})

describe('RUN_ABORTED action', () => {
  it('sets status to aborted and clears isAborting when getRun returns aborted status', async () => {
    const { getRun } = jest.requireMock('@/lib/api-client')
    const { createSSEConnection } = jest.requireMock('@/lib/sse')
    jest.clearAllMocks()

    getRun.mockResolvedValueOnce({
      id: 'abort1',
      ticker: 'TSLA',
      date: '2026-03-23',
      status: 'aborted',
      decision: null,
      created_at: '2026-03-23T00:00:00Z',
      config: null,
      reports: { 'market_analyst:0': 'partial report' },
      error: null,
      token_usage: null,
    })

    const { result } = renderHook(() => useRunStream('abort1'))
    await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

    expect(result.current.status).toBe('aborted')
    expect(result.current.isAborting).toBe(false)
    expect(createSSEConnection).not.toHaveBeenCalled()
    // Partial reports hydrated before aborting
    expect(result.current.reports['market_analyst']).toEqual(['partial report'])
  })

  it('sets status to aborted when SSE fires onRunAborted', async () => {
    const { getRun } = jest.requireMock('@/lib/api-client')
    const { createSSEConnection } = jest.requireMock('@/lib/sse')
    jest.clearAllMocks()

    getRun.mockResolvedValueOnce({
      id: 'abort2',
      ticker: 'TSLA',
      date: '2026-03-23',
      status: 'queued',
      decision: null,
      created_at: '2026-03-23T00:00:00Z',
      config: null,
      reports: {},
      error: null,
      token_usage: null,
    })

    createSSEConnection.mockImplementationOnce(
      (_url: string, handlers: Record<string, (d: unknown) => void>) => {
        setTimeout(() => {
          handlers.onAgentStart?.({ step: 'bull_researcher', turn: 0 })
          handlers.onRunAborted?.({ run_id: 'abort2' })
        }, 0)
        return jest.fn()
      }
    )

    const { result } = renderHook(() => useRunStream('abort2'))
    await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

    expect(result.current.status).toBe('aborted')
    expect(result.current.isAborting).toBe(false)
  })

  it('abortRun sets isAborting to true and calls api.abortRun', async () => {
    const { getRun, abortRun: abortRunMock } = jest.requireMock('@/lib/api-client')
    jest.clearAllMocks()

    getRun.mockResolvedValue({
      id: 'abort3',
      ticker: 'MSFT',
      date: '2026-03-23',
      status: 'queued',
      decision: null,
      created_at: '2026-03-23T00:00:00Z',
      config: null,
      reports: {},
      error: null,
    })

    abortRunMock.mockResolvedValue({ status: 'aborted' })

    const { result } = renderHook(() => useRunStream('abort3'))
    await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

    // Trigger abortRun — isAborting should become true immediately
    await act(async () => {
      await result.current.abortRun()
    })

    expect(abortRunMock).toHaveBeenCalledWith('abort3')
  })

  it('resets isAborting to false when api.abortRun throws', async () => {
    const { getRun, abortRun: abortRunMock } = jest.requireMock('@/lib/api-client')
    jest.clearAllMocks()

    getRun.mockResolvedValue({
      id: 'abort4',
      ticker: 'MSFT',
      date: '2026-03-23',
      status: 'queued',
      decision: null,
      created_at: '2026-03-23T00:00:00Z',
      config: null,
      reports: {},
      error: null,
    })

    abortRunMock.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useRunStream('abort4'))
    await act(async () => { await new Promise((r) => setTimeout(r, 10)) })

    await act(async () => {
      await result.current.abortRun()
    })

    expect(result.current.isAborting).toBe(false)
  })
})
