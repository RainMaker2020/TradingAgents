import { renderHook, waitFor } from '@testing-library/react'
import { useWorkspaceRuntime, __resetWorkspaceRuntimeCacheForTests } from '@/features/dashboard/hooks/useWorkspaceRuntime'

jest.mock('@/lib/api-client', () => ({
  getRuntimeSnapshot: jest.fn(),
}))

const apiClient = jest.requireMock('@/lib/api-client') as {
  getRuntimeSnapshot: jest.Mock
}

const runtimeSnapshot = {
  health: {
    api_available: true,
    sse_supported: true,
    api_version: '0.2.1',
    server_time: '2026-03-25T00:00:00Z',
    runtime_mode: 'development',
  },
  session: {
    total_runs: 10,
    queued_runs: 1,
    running_runs: 2,
    complete_runs: 6,
    error_runs: 1,
    latest_run_id: 'abcd1234',
  },
  constraints: {
    min_rounds: 1,
    max_rounds: 5,
  },
  defaults: {
    deep_think_llm: 'gpt-5.2',
    quick_think_llm: 'gpt-5-mini',
    llm_provider: 'openai',
    max_debate_rounds: 1,
    max_risk_discuss_rounds: 1,
  },
}

beforeEach(() => {
  __resetWorkspaceRuntimeCacheForTests()
  apiClient.getRuntimeSnapshot.mockReset()
})

test('deduplicates in-flight request across hook instances', async () => {
  apiClient.getRuntimeSnapshot.mockResolvedValue(runtimeSnapshot)

  const { result } = renderHook(() => {
    const first = useWorkspaceRuntime()
    const second = useWorkspaceRuntime()
    return { first, second }
  })

  await waitFor(() => expect(result.current.first.loading).toBe(false))

  expect(apiClient.getRuntimeSnapshot).toHaveBeenCalledTimes(1)
  expect(result.current.first.runTotals.state).toBe('available')
  expect(result.current.second.runTotals.state).toBe('available')
})

test('returns unknown states when runtime snapshot fails', async () => {
  apiClient.getRuntimeSnapshot.mockRejectedValue(new Error('network down'))

  const { result } = renderHook(() => useWorkspaceRuntime())

  await waitFor(() => expect(result.current.loading).toBe(false))

  expect(result.current.apiReachable.state).toBe('unknown')
  expect(result.current.sseReady.state).toBe('unknown')
  expect(result.current.runTotals.state).toBe('unknown')
  expect(result.current.settings.state).toBe('unknown')
})
