'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ApiError, createRun } from '@/lib/api-client'
import type { RunConfig } from '@/lib/types/run'
import type { NewRunFormState } from '../types'

type SimulationFieldErrors = Partial<Record<
  'initial_cash' | 'slippage_bps' | 'fee_per_trade' | 'max_position_pct',
  string
>>

export function useRunSubmit() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (
    form: NewRunFormState,
    onSimulationFieldErrors?: (errors: SimulationFieldErrors) => void,
  ) => {
    setLoading(true)
    setError(null)
    try {
      const payload: RunConfig = {
        ticker: form.ticker,
        date: form.date,
        llm_provider: form.llm_provider,
        deep_think_llm: form.deep_think_llm,
        quick_think_llm: form.quick_think_llm,
        max_debate_rounds: form.max_debate_rounds,
        max_risk_discuss_rounds: form.max_risk_discuss_rounds,
        enabled_analysts: form.enabled_analysts,
        simulation_config: {
          initial_cash: form.initial_cash,
          slippage_bps: form.slippage_bps,
          fee_per_trade: form.fee_per_trade,
          max_position_pct: form.max_position_pct,
        },
      }
      const run = await createRun(payload)
      router.push(`/runs/${run.id}`)
    } catch (e) {
      if (e instanceof ApiError && e.status === 422 && Array.isArray(e.detail)) {
        const fieldErrors: SimulationFieldErrors = {}
        for (const issue of e.detail) {
          if (
            typeof issue === 'object' &&
            issue !== null &&
            Array.isArray((issue as { loc?: unknown[] }).loc)
          ) {
            const loc = (issue as { loc: unknown[] }).loc.map(String)
            const field = loc[loc.length - 1]
            const message =
              typeof (issue as { msg?: unknown }).msg === 'string'
                ? (issue as { msg: string }).msg
                : 'Invalid value'
            if (
              loc.includes('simulation_config') &&
              ['initial_cash', 'slippage_bps', 'fee_per_trade', 'max_position_pct'].includes(field)
            ) {
              fieldErrors[field as keyof SimulationFieldErrors] = message
            }
          }
        }
        if (Object.keys(fieldErrors).length > 0) {
          onSimulationFieldErrors?.(fieldErrors)
          setError('Please correct the highlighted simulation fields.')
          return
        }
      }
      setError(e instanceof Error ? e.message : 'Failed to start run')
    } finally {
      setLoading(false)
    }
  }

  return { submit, loading, error }
}
