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

export const PROVIDER_MODEL_DEFAULTS: Record<string, { deep: string; quick: string }> = {
  openai:    { deep: 'gpt-5.2',           quick: 'gpt-5-mini' },
  anthropic: { deep: 'claude-opus-4-6',   quick: 'claude-haiku-4-5' },
  google:    { deep: 'gemini-2.5-pro',    quick: 'gemini-2.5-flash' },
  deepseek:  { deep: 'deepseek-reasoner', quick: 'deepseek-chat' },
}
