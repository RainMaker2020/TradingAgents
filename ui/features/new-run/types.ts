import { DEFAULT_ENABLED_ANALYSTS, DEFAULT_WORKSPACE_SETTINGS } from '@/lib/defaults'

export type NewRunFormState = {
  ticker: string
  date: string
  llm_provider: string
  deep_think_llm: string
  quick_think_llm: string
  max_debate_rounds: number
  max_risk_discuss_rounds: number
  enabled_analysts: string[]
}

export const DEFAULT_FORM: NewRunFormState = {
  ticker: '',
  date: '',
  llm_provider: DEFAULT_WORKSPACE_SETTINGS.llm_provider,
  deep_think_llm: DEFAULT_WORKSPACE_SETTINGS.deep_think_llm,
  quick_think_llm: DEFAULT_WORKSPACE_SETTINGS.quick_think_llm,
  max_debate_rounds: DEFAULT_WORKSPACE_SETTINGS.max_debate_rounds,
  max_risk_discuss_rounds: DEFAULT_WORKSPACE_SETTINGS.max_risk_discuss_rounds,
  enabled_analysts: [...DEFAULT_ENABLED_ANALYSTS],
}
