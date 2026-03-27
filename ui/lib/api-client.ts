import type { RunConfig, RunSummary } from './types/run'
import type { Settings } from './types/settings'
import type { ProviderModels, RuntimeHealth, RuntimeSnapshot } from './types/system'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

export class ApiError extends Error {
  status: number
  path: string
  detail?: unknown

  constructor(message: string, status: number, path: string, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.path = path
    this.detail = detail
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase()
  const hasBody = ['POST', 'PUT', 'PATCH'].includes(method)
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: hasBody
      ? { 'Content-Type': 'application/json', ...init?.headers }
      : init?.headers,
  })
  if (!res.ok) {
    let errorBody: unknown = undefined
    try {
      errorBody = await res.json()
    } catch {
      // Some endpoints may return non-JSON bodies on failure.
    }
    const detail =
      typeof errorBody === 'object' && errorBody !== null && 'detail' in errorBody
        ? (errorBody as { detail?: unknown }).detail
        : undefined
    throw new ApiError(`API error ${res.status}: ${path}`, res.status, path, detail)
  }
  return res.json() as Promise<T>
}

export type RunResult = RunSummary & {
  config: RunConfig | null
  reports: Record<string, string>
  error: string | null
  token_usage: Record<string, { tokens_in: number; tokens_out: number }> | null
}

export const createRun = (config: RunConfig): Promise<RunSummary> =>
  apiFetch('/api/runs', { method: 'POST', body: JSON.stringify(config) })

export const listRuns = (): Promise<RunSummary[]> =>
  apiFetch('/api/runs')

export const getRun = (id: string): Promise<RunResult> =>
  apiFetch<RunResult>(`/api/runs/${id}`)

export const getSettings = (): Promise<Settings> =>
  apiFetch('/api/settings')

export const updateSettings = (settings: Settings): Promise<Settings> =>
  apiFetch('/api/settings', { method: 'PUT', body: JSON.stringify(settings) })

export const getSystemHealth = (): Promise<RuntimeHealth> =>
  apiFetch('/api/system/health')

export const getRuntimeSnapshot = (): Promise<RuntimeSnapshot> =>
  apiFetch('/api/system/runtime')

export const getProviderModels = (provider: string): Promise<ProviderModels> =>
  apiFetch(`/api/system/models/${encodeURIComponent(provider)}`)

export const getRunStreamUrl = (id: string): string =>
  `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/runs/${id}/stream`

export const abortRun = (id: string): Promise<{ status: string }> =>
  apiFetch(`/api/runs/${id}/abort`, { method: 'POST' })
