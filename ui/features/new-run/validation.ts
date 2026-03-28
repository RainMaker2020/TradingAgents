import { RUN_LIMITS } from '@/lib/defaults'
import type { NewRunFormState } from './types'

export type SimulationFieldKey = 'initial_cash' | 'slippage_bps' | 'fee_per_trade' | 'max_position_pct'

export type RunTargetFieldKey =
  | 'ticker'
  | 'date'
  | 'end_date'
  | 'max_debate_rounds'
  | 'max_risk_discuss_rounds'

export type SimulationErrors = Partial<Record<SimulationFieldKey, string>>
export type RunTargetErrors = Partial<Record<RunTargetFieldKey, string>>

const TICKER_RE = /^[A-Z]{1,10}$/
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/

function isFutureCalendarDate(iso: string): boolean {
  if (!ISO_DATE_RE.test(iso)) return false
  const d = new Date(`${iso}T12:00:00.000Z`)
  const today = new Date()
  const utcMid = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate())
  return d.getTime() > utcMid
}

/** Simulation block — same rules as API `SimulationConfigSchema`. */
export function validateSimulationConfig(state: NewRunFormState): SimulationErrors {
  const errors: SimulationErrors = {}
  if (!Number.isFinite(state.initial_cash) || state.initial_cash <= 0) {
    errors.initial_cash = 'Initial Cash ($) must be greater than 0.'
  }
  if (!Number.isFinite(state.slippage_bps) || state.slippage_bps < 0) {
    errors.slippage_bps = 'Slippage (bps) must be 0 or greater.'
  }
  if (!Number.isFinite(state.fee_per_trade) || state.fee_per_trade < 0) {
    errors.fee_per_trade = 'Fee Per Trade ($) must be 0 or greater.'
  }
  if (
    !Number.isFinite(state.max_position_pct) ||
    state.max_position_pct <= 0 ||
    state.max_position_pct > 100
  ) {
    errors.max_position_pct = 'Max Position Size (%) must be between 0 and 100.'
  }
  return errors
}

/** Analysis target + LLM round fields (client-side; mirrors API bounds where applicable). */
export function validateRunTarget(form: NewRunFormState): RunTargetErrors {
  const errors: RunTargetErrors = {}
  const t = form.ticker.trim().toUpperCase()
  if (!t) {
    errors.ticker = 'Ticker symbol is required.'
  } else if (!TICKER_RE.test(t)) {
    errors.ticker = 'Use 1–10 uppercase letters (e.g. NVDA).'
  }

  const dateStr = form.date?.trim() ?? ''
  if (!dateStr) {
    errors.date = 'Trade date is required.'
  } else if (!ISO_DATE_RE.test(dateStr)) {
    errors.date = 'Use a valid date (YYYY-MM-DD).'
  } else if (isFutureCalendarDate(dateStr)) {
    errors.date = 'Trade date cannot be in the future.'
  }

  if (form.mode === 'backtest') {
    const endStr = form.end_date?.trim() ?? ''
    if (endStr) {
      if (!ISO_DATE_RE.test(endStr)) {
        errors.end_date = 'Use a valid end date (YYYY-MM-DD).'
      } else if (isFutureCalendarDate(endStr)) {
        errors.end_date = 'End date cannot be in the future.'
      } else if (dateStr && ISO_DATE_RE.test(dateStr) && endStr < dateStr) {
        errors.end_date = 'End date must be on or after trade date.'
      }
    }
  }

  const dr = form.max_debate_rounds
  if (
    !Number.isFinite(dr) ||
    !Number.isInteger(dr) ||
    dr < RUN_LIMITS.minRounds ||
    dr > RUN_LIMITS.maxRounds
  ) {
    errors.max_debate_rounds = `Debate rounds must be a whole number between ${RUN_LIMITS.minRounds} and ${RUN_LIMITS.maxRounds}.`
  }

  const rr = form.max_risk_discuss_rounds
  if (
    !Number.isFinite(rr) ||
    !Number.isInteger(rr) ||
    rr < RUN_LIMITS.minRounds ||
    rr > RUN_LIMITS.maxRounds
  ) {
    errors.max_risk_discuss_rounds = `Risk discussion rounds must be a whole number between ${RUN_LIMITS.minRounds} and ${RUN_LIMITS.maxRounds}.`
  }

  return errors
}

export function hasBlockingRunErrors(form: NewRunFormState): boolean {
  return (
    Object.keys(validateRunTarget(form)).length > 0 ||
    Object.keys(validateSimulationConfig(form)).length > 0
  )
}
