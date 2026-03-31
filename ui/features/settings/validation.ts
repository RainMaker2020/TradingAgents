import { RUN_LIMITS } from '@/lib/defaults'
import type { SettingsFormState } from './types'

export type SettingsFieldErrors = Partial<
  Record<'max_debate_rounds' | 'max_risk_discuss_rounds' | 'deep_think_llm' | 'quick_think_llm', string>
>

export function validateSettingsForm(form: SettingsFormState): SettingsFieldErrors {
  const errors: SettingsFieldErrors = {}

  const dr = form.max_debate_rounds
  if (
    !Number.isFinite(dr) ||
    !Number.isInteger(dr) ||
    dr < RUN_LIMITS.minRounds ||
    dr > RUN_LIMITS.maxRounds
  ) {
    errors.max_debate_rounds = `Must be a whole number between ${RUN_LIMITS.minRounds} and ${RUN_LIMITS.maxRounds}.`
  }

  const rr = form.max_risk_discuss_rounds
  if (
    !Number.isFinite(rr) ||
    !Number.isInteger(rr) ||
    rr < RUN_LIMITS.minRounds ||
    rr > RUN_LIMITS.maxRounds
  ) {
    errors.max_risk_discuss_rounds = `Must be a whole number between ${RUN_LIMITS.minRounds} and ${RUN_LIMITS.maxRounds}.`
  }

  if (!form.deep_think_llm?.trim()) {
    errors.deep_think_llm = 'Deep think model is required.'
  }
  if (!form.quick_think_llm?.trim()) {
    errors.quick_think_llm = 'Quick think model is required.'
  }

  return errors
}
