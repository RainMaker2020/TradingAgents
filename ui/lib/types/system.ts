import type { Settings } from './settings'

export type RuntimeHealth = {
  api_available: boolean
  sse_supported: boolean
  api_version: string
  server_time: string
  runtime_mode: string
}

export type SessionStats = {
  total_runs: number
  queued_runs: number
  running_runs: number
  complete_runs: number
  error_runs: number
  latest_run_id: string | null
}

export type RuntimeConstraints = {
  min_rounds: number
  max_rounds: number
}

export type RuntimeSnapshot = {
  health: RuntimeHealth
  session: SessionStats
  constraints: RuntimeConstraints
  defaults: Settings
}

export type ProviderModels = {
  provider: string
  models: string[]
  error: string | null
}

/** GET /api/symbols/resolve — Yahoo Finance validation before launch */
export type TickerResolveResponse = {
  valid: boolean
  query: string
  yahoo_symbol: string
  display_name: string | null
  message: string | null
}
