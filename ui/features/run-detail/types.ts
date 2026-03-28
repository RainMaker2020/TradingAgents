import type { AgentStep, RunStatus, BacktestMetrics, BacktestTraceEvent } from '@/lib/types/run'
import type { Decision, StepStatus, ChiefAnalystReport } from '@/lib/types/agents'

export type TokenCount = { in: number; out: number }

export type RunStreamState = {
  status: RunStatus | 'connecting'
  steps: Record<AgentStep, StepStatus>
  reports: Record<AgentStep, string[]>
  backtestSummary: string | null
  /** Layer 2: one-line scan summary from server (same facts as metrics). */
  backtestHeadline: string | null
  backtestMetrics: BacktestMetrics | null
  /** Persisted `BacktestEvent` timeline from the engine (backtest runs). */
  backtestTrace: BacktestTraceEvent[] | null
  mode: 'graph' | 'backtest' | null
  endDate: string | null
  verdict: Decision | null
  error: string | null
  tokensByStep: Record<AgentStep, TokenCount>
  tokensTotal: TokenCount
  chiefAnalystReport: ChiefAnalystReport | null
  ticker: string | null
  date: string | null
  /** From persisted run config — models used for this run */
  llmProvider: string | null
  deepThinkLlm: string | null
  quickThinkLlm: string | null
}
