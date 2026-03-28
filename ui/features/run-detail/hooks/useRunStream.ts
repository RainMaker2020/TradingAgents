'use client'
import { useEffect, useReducer, useState, useCallback } from 'react'
import { createSSEConnection } from '@/lib/sse'
import { getRun, getRunStreamUrl } from '@/lib/api-client'
import * as api from '@/lib/api-client'
import { parseBacktestMetrics } from '@/lib/backtestMetricsParse'
import { normalizeBacktestTrace } from '@/lib/backtestTrace'
import { AGENT_STEPS } from '@/lib/types/run'
import type { AgentStep, BacktestMetrics, BacktestTraceEvent } from '@/lib/types/run'
import type { ChiefAnalystReport } from '@/lib/types/agents'
import type { RunStreamState, TokenCount } from '../types'

const zeroTokens = (): TokenCount => ({ in: 0, out: 0 })

const initialState: RunStreamState = {
  status: 'connecting',
  steps:        Object.fromEntries(AGENT_STEPS.map((s) => [s, 'pending'])) as RunStreamState['steps'],
  reports:      Object.fromEntries(AGENT_STEPS.map((s) => [s, []])) as unknown as RunStreamState['reports'],
  backtestSummary: null,
  backtestHeadline: null,
  backtestMetrics: null,
  backtestTrace: null,
  mode: null,
  endDate: null,
  tokensByStep: Object.fromEntries(AGENT_STEPS.map((s) => [s, zeroTokens()])) as RunStreamState['tokensByStep'],
  tokensTotal:  zeroTokens(),
  verdict: null,
  error: null,
  chiefAnalystReport: null,
  ticker: null,
  date: null,
  llmProvider: null,
  deepThinkLlm: null,
  quickThinkLlm: null,
}

type Action =
  | { type: 'AGENT_START';    step: AgentStep; turn: number }
  | { type: 'AGENT_COMPLETE'; step: AgentStep; turn: number; report: string; tokens_in?: number; tokens_out?: number }
  | { type: 'RUN_COMPLETE';   decision: string }
  | { type: 'RUN_ERROR';      message: string }
  | { type: 'RUN_ABORTED' }
  | { type: 'CONNECTED' }
  | { type: 'RESET' }
  | {
      type: 'HYDRATE_META'
      ticker: string
      date: string
      mode: 'graph' | 'backtest' | null
      endDate: string | null
      llmProvider: string | null
      deepThinkLlm: string | null
      quickThinkLlm: string | null
    }
  | { type: 'BACKTEST_SUMMARY'; summary: string }
  | { type: 'BACKTEST_HEADLINE'; headline: string }
  | { type: 'BACKTEST_METRICS'; metrics: BacktestMetrics }
  | { type: 'BACKTEST_TRACE'; trace: BacktestTraceEvent[] | null }

function reducer(state: RunStreamState, action: Action): RunStreamState {
  switch (action.type) {
    case 'CONNECTED':
      return { ...state, status: 'running' }

    case 'RESET':
      return initialState

    case 'AGENT_START':
      if (state.steps[action.step] !== 'pending') return state
      return { ...state, steps: { ...state.steps, [action.step]: 'running' } }

    case 'AGENT_COMPLETE': {
      const dIn  = action.tokens_in  ?? 0
      const dOut = action.tokens_out ?? 0
      const prev = state.tokensByStep[action.step] ?? zeroTokens()
      const existingStepReports = state.reports[action.step] ?? []
      const turnIndex = Number.isInteger(action.turn) && action.turn >= 0
        ? action.turn
        : existingStepReports.length
      const hasReportForTurn = typeof existingStepReports[turnIndex] === 'string'
      const nextStepReports = [...existingStepReports]
      nextStepReports[turnIndex] = action.report

      let chiefAnalystReport: ChiefAnalystReport | null = state.chiefAnalystReport
      if (action.step === 'chief_analyst') {
        try { chiefAnalystReport = JSON.parse(action.report) as ChiefAnalystReport }
        catch { chiefAnalystReport = null }
      }

      return {
        ...state,
        steps:   { ...state.steps,   [action.step]: 'done' },
        reports: {
          ...state.reports,
          [action.step]: nextStepReports,
        },
        tokensByStep: {
          ...state.tokensByStep,
          // Prevent double counting when duplicate completion events replay.
          [action.step]: hasReportForTurn ? prev : { in: prev.in + dIn, out: prev.out + dOut },
        },
        tokensTotal: {
          in:  hasReportForTurn ? state.tokensTotal.in  : state.tokensTotal.in  + dIn,
          out: hasReportForTurn ? state.tokensTotal.out : state.tokensTotal.out + dOut,
        },
        chiefAnalystReport,
      }
    }

    case 'RUN_COMPLETE':
      return { ...state, status: 'complete', verdict: action.decision as RunStreamState['verdict'] }

    case 'RUN_ERROR':
      return { ...state, status: 'error', error: action.message }

    case 'RUN_ABORTED':
      return { ...state, status: 'aborted', error: null }

    case 'HYDRATE_META':
      return {
        ...state,
        ticker: action.ticker,
        date: action.date,
        mode: action.mode,
        endDate: action.endDate,
        llmProvider: action.llmProvider,
        deepThinkLlm: action.deepThinkLlm,
        quickThinkLlm: action.quickThinkLlm,
      }

    case 'BACKTEST_SUMMARY':
      return { ...state, backtestSummary: action.summary }

    case 'BACKTEST_HEADLINE':
      return { ...state, backtestHeadline: action.headline }

    case 'BACKTEST_METRICS':
      return {
        ...state,
        backtestMetrics: action.metrics,
        tokensTotal: {
          in: action.metrics.llm_tokens_in ?? 0,
          out: action.metrics.llm_tokens_out ?? 0,
        },
      }

    case 'BACKTEST_TRACE':
      return { ...state, backtestTrace: action.trace }

    default:
      return state
  }
}

export function useRunStream(runId: string): RunStreamState & { abortRun: () => Promise<void>; isAborting: boolean } {
  const [state, dispatch] = useReducer(reducer, initialState)
  const [isAborting, setIsAborting] = useState(false)

  // Clear isAborting when any terminal state arrives (including SSE disconnect fallback)
  useEffect(() => {
    if (state.status === 'complete' || state.status === 'error' || state.status === 'aborted') {
      setIsAborting(false)
    }
  }, [state.status])

  const abortRun = useCallback(async () => {
    setIsAborting(true)
    try {
      await api.abortRun(runId)
    } catch {
      setIsAborting(false)
      // Toast: component layer should handle UI feedback if needed
    }
  }, [runId])

  useEffect(() => {
    dispatch({ type: 'RESET' })
    let close: (() => void) | undefined
    let aborted = false

    getRun(runId, { includeBacktestTrace: true }).then((run) => {
      if (aborted) return
      dispatch({
        type: 'HYDRATE_META',
        ticker: run.ticker,
        date: run.date,
        mode: run.config?.mode ?? null,
        endDate: run.config?.end_date ?? null,
        llmProvider: run.config?.llm_provider ?? null,
        deepThinkLlm: run.config?.deep_think_llm ?? null,
        quickThinkLlm: run.config?.quick_think_llm ?? null,
      })

      if (run.status === 'complete' && Object.keys(run.reports).length > 0) {
        dispatch({ type: 'CONNECTED' })
        for (const [key, report] of Object.entries(run.reports)) {
          const lastColon = key.lastIndexOf(':')
          if (lastColon === -1) continue
          const step  = key.slice(0, lastColon)
          if (step === 'backtest_summary') {
            dispatch({ type: 'BACKTEST_SUMMARY', summary: report })
            continue
          }
          if (step === 'backtest_headline') {
            dispatch({ type: 'BACKTEST_HEADLINE', headline: report })
            continue
          }
          if (step === 'backtest_metrics') {
            const metrics = parseBacktestMetrics(report)
            if (metrics) dispatch({ type: 'BACKTEST_METRICS', metrics })
            continue
          }
          const turn  = parseInt(key.slice(lastColon + 1), 10)
          if (!Number.isFinite(turn)) continue
          const tok   = run.token_usage?.[key] ?? { tokens_in: 0, tokens_out: 0 }
          dispatch({ type: 'AGENT_START', step: step as AgentStep, turn })
          dispatch({ type: 'AGENT_COMPLETE', step: step as AgentStep, turn, report,
                     tokens_in: tok.tokens_in, tokens_out: tok.tokens_out })
        }
        const hydratedTrace = normalizeBacktestTrace(run.backtest_trace)
        if (hydratedTrace.length > 0) {
          dispatch({ type: 'BACKTEST_TRACE', trace: hydratedTrace })
        }
        dispatch({ type: 'RUN_COMPLETE', decision: run.decision ?? 'HOLD' })
        return
      }

      if (run.status === 'aborted') {
        dispatch({ type: 'CONNECTED' })
        for (const [key, report] of Object.entries(run.reports)) {
          const lastColon = key.lastIndexOf(':')
          if (lastColon === -1) continue
          const step = key.slice(0, lastColon)
          if (step === 'backtest_summary') {
            dispatch({ type: 'BACKTEST_SUMMARY', summary: report })
            continue
          }
          if (step === 'backtest_headline') {
            dispatch({ type: 'BACKTEST_HEADLINE', headline: report })
            continue
          }
          if (step === 'backtest_metrics') {
            const metrics = parseBacktestMetrics(report)
            if (metrics) dispatch({ type: 'BACKTEST_METRICS', metrics })
            continue
          }
          const turn = parseInt(key.slice(lastColon + 1), 10)
          if (!Number.isFinite(turn)) continue
          const tok  = run.token_usage?.[key] ?? { tokens_in: 0, tokens_out: 0 }
          dispatch({ type: 'AGENT_START', step: step as AgentStep, turn })
          dispatch({ type: 'AGENT_COMPLETE', step: step as AgentStep, turn, report,
                     tokens_in: tok.tokens_in, tokens_out: tok.tokens_out })
        }
        const abortedTrace = normalizeBacktestTrace(run.backtest_trace)
        if (abortedTrace.length > 0) {
          dispatch({ type: 'BACKTEST_TRACE', trace: abortedTrace })
        }
        dispatch({ type: 'RUN_ABORTED' })
        return
      }

      const url = getRunStreamUrl(runId)
      close = createSSEConnection(url, {
        onOpen:          () => dispatch({ type: 'CONNECTED' }),
        onAgentStart:    ({ step, turn }) => {
          if (step === 'backtest_summary') return
          if (step === 'backtest_headline') return
          if (step === 'backtest_metrics') return
          dispatch({ type: 'AGENT_START', step: step as AgentStep, turn })
        },
        onAgentComplete: ({ step, turn, report, tokens_in, tokens_out }) => {
          if (step === 'backtest_summary') {
            dispatch({ type: 'BACKTEST_SUMMARY', summary: report })
            return
          }
          if (step === 'backtest_headline') {
            dispatch({ type: 'BACKTEST_HEADLINE', headline: report })
            return
          }
          if (step === 'backtest_metrics') {
            const metrics = parseBacktestMetrics(report)
            if (metrics) dispatch({ type: 'BACKTEST_METRICS', metrics })
            return
          }
          dispatch({
            type: 'AGENT_COMPLETE',
            step: step as AgentStep,
            turn,
            report,
            tokens_in,
            tokens_out,
          })
        },
        onRunComplete:   ({ decision }) => {
          dispatch({ type: 'RUN_COMPLETE', decision })
          getRun(runId, { includeBacktestTrace: true }).then((r) => {
            if (aborted) return
            const t = normalizeBacktestTrace(r.backtest_trace)
            if (t.length > 0) dispatch({ type: 'BACKTEST_TRACE', trace: t })
          }).catch(() => { /* trace is optional */ })
        },
        onRunError:      ({ message })  => dispatch({ type: 'RUN_ERROR',    message }),
        onRunAborted:    () => {
          dispatch({ type: 'RUN_ABORTED' })
          getRun(runId, { includeBacktestTrace: true }).then((r) => {
            if (aborted) return
            const t = normalizeBacktestTrace(r.backtest_trace)
            if (t.length > 0) dispatch({ type: 'BACKTEST_TRACE', trace: t })
          }).catch(() => { /* trace is optional */ })
        },
      })
    }).catch(() => {
      if (!aborted) dispatch({ type: 'RUN_ERROR', message: 'Failed to load run' })
    })

    return () => { aborted = true; close?.() }
  }, [runId])

  return { ...state, abortRun, isAborting }
}
