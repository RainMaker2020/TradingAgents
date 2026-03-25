export const RUN_LIMITS = {
  minRounds: 1,
  maxRounds: 5,
} as const

export const DEFAULT_ENABLED_ANALYSTS = ['market', 'news', 'fundamentals', 'social'] as const

export const DEFAULT_WORKSPACE_SETTINGS = {
  llm_provider: 'openai',
  deep_think_llm: 'gpt-5.2',
  quick_think_llm: 'gpt-5-mini',
  max_debate_rounds: 1,
  max_risk_discuss_rounds: 1,
} as const
