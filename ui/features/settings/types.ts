export type SettingsFormState = {
  llm_provider: string
  deep_think_llm: string
  quick_think_llm: string
  max_debate_rounds: number
  max_risk_discuss_rounds: number
  execution_mode: 'graph' | 'backtest'
  profile_preset: 'fast' | 'balanced' | 'deep' | null
}
