import { createRun, listRuns, getSettings } from '@/lib/api-client'

global.fetch = jest.fn()

beforeEach(() => jest.clearAllMocks())

test('createRun POSTs to /api/runs and returns run summary', async () => {
  const mockRun = { id: 'abc123', ticker: 'NVDA', status: 'queued' }
  ;(fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockRun,
  })
  const result = await createRun({
    ticker: 'NVDA', date: '2024-05-10',
    llm_provider: 'openai', deep_think_llm: 'gpt-5.2',
    quick_think_llm: 'gpt-5-mini', max_debate_rounds: 1,
    max_risk_discuss_rounds: 1,
    simulation_config: {
      initial_cash: 100000,
      slippage_bps: 5,
      fee_per_trade: 1,
      max_position_pct: 10, // percent, not ratio
    },
  })
  expect(fetch).toHaveBeenCalledWith('/api/runs', expect.objectContaining({ method: 'POST' }))
  const requestInit = (fetch as jest.Mock).mock.calls[0][1] as RequestInit
  const body = JSON.parse(String(requestInit.body))
  expect(body.simulation_config.max_position_pct).toBe(10)
  expect(result.id).toBe('abc123')
})

test('listRuns GETs /api/runs', async () => {
  ;(fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => [] })
  const result = await listRuns()
  expect(fetch).toHaveBeenCalledWith('/api/runs', expect.objectContaining({ headers: undefined }))
  expect(Array.isArray(result)).toBe(true)
})
