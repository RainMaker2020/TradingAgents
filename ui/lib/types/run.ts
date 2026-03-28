export type AgentStep =
  | 'market_analyst'
  | 'news_analyst'
  | 'fundamentals_analyst'
  | 'social_analyst'
  | 'bull_researcher'
  | 'bear_researcher'
  | 'research_manager'
  | 'trader'
  | 'aggressive_analyst'
  | 'conservative_analyst'
  | 'neutral_analyst'
  | 'risk_judge'
  | 'chief_analyst'

export const AGENT_STEPS: AgentStep[] = [
  'market_analyst', 'news_analyst', 'fundamentals_analyst', 'social_analyst',
  'bull_researcher', 'bear_researcher', 'research_manager',
  'trader',
  'aggressive_analyst', 'conservative_analyst', 'neutral_analyst', 'risk_judge',
  'chief_analyst',
]

export const AGENT_STEP_LABELS: Record<AgentStep, string> = {
  market_analyst:       'Market',
  news_analyst:         'News',
  fundamentals_analyst: 'Fundamentals',
  social_analyst:       'Social',
  bull_researcher:      'Bull Researcher',
  bear_researcher:      'Bear Researcher',
  research_manager:     'Research Manager',
  trader:               'Trader',
  aggressive_analyst:   'Aggressive',
  conservative_analyst: 'Conservative',
  neutral_analyst:      'Neutral',
  risk_judge:           'Risk Judge',
  chief_analyst:        'Chief Analyst',
}

export const STEP_PHASE: Record<AgentStep, 'analysts' | 'researchers' | 'trader' | 'risk' | 'summary'> = {
  market_analyst:       'analysts',
  news_analyst:         'analysts',
  fundamentals_analyst: 'analysts',
  social_analyst:       'analysts',
  bull_researcher:      'researchers',
  bear_researcher:      'researchers',
  research_manager:     'researchers',
  trader:               'trader',
  aggressive_analyst:   'risk',
  conservative_analyst: 'risk',
  neutral_analyst:      'risk',
  risk_judge:           'risk',
  chief_analyst:        'summary',
}

export type RunStatus = 'queued' | 'running' | 'complete' | 'error' | 'aborted'

export type SimulationConfig = {
  initial_cash: number
  slippage_bps: number
  fee_per_trade: number
  max_position_pct: number
}

export type RunConfig = {
  ticker: string
  date: string
  llm_provider: string
  deep_think_llm: string
  quick_think_llm: string
  max_debate_rounds: number
  max_risk_discuss_rounds: number
  enabled_analysts?: string[]
  simulation_config?: SimulationConfig
  mode?: 'graph' | 'backtest'
  end_date?: string | null
}

export type RunSummary = {
  id: string
  ticker: string
  date: string
  status: RunStatus
  /** graph = LLM pipeline; backtest = execution engine (API always sends; omit in mocks = graph) */
  mode?: 'graph' | 'backtest'
  decision: 'BUY' | 'SELL' | 'HOLD' | null
  created_at: string
}

/** End-of-run exposure (backtest); not an intraday trade signal. */
export type BacktestTerminalExposure = 'long' | 'flat_closed' | 'flat_untraded'

export type BacktestMetrics = {
  initial_cash: number
  final_equity: number
  /** null when initial cash is zero (return not defined). */
  total_return_pct: number | null
  unrealized_pnl: number
  realized_pnl: number
  total_fees_paid: number
  fill_count: number
  max_drawdown_pct: number | null
  as_of: string | null
  positions: Record<string, string>
  terminal_exposure: BacktestTerminalExposure
}

/** One row from `RunsStore.backtest_trace` (serialized `BacktestEvent`). */
export type BacktestTraceEvent = {
  event_type?: string
  timestamp?: string
  symbol?: string
  detail?: string | null
  signal?: Record<string, unknown> | null
  fill?: Record<string, unknown> | null
  rejection?: { code?: string; detail?: string } | null
  order?: Record<string, unknown> | null
}
