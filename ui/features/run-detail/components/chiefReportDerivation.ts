import { AGENT_STEP_LABELS } from '@/lib/types/run'
import type { AgentStep } from '@/lib/types/run'
import type { ChiefAnalystReport } from '@/lib/types/agents'

const INSUFFICIENT_EVIDENCE = 'Insufficient evidence'

export type ChiefScenario = {
  name: 'Bull' | 'Base' | 'Bear'
  thesis: string
  trigger: string
}

export type ChiefReportViewModel = {
  timeHorizon: string
  timeHorizonConfidence: 'high' | 'medium' | 'low'
  scenarioMatrix: ChiefScenario[]
  sourcesSummary: string
}

function firstSentence(value: string | null | undefined): string {
  const normalized = (value ?? '').trim()
  if (!normalized) return INSUFFICIENT_EVIDENCE
  const sentence = normalized.split(/[.!?]/)[0]?.trim()
  return sentence && sentence.length > 0 ? sentence : normalized
}

function summarizeContributor(steps: AgentStep[]): string {
  if (steps.length === 0) return 'no upstream agent notes'
  if (steps.length === 1) return AGENT_STEP_LABELS[steps[0]]
  if (steps.length === 2) return `${AGENT_STEP_LABELS[steps[0]]} and ${AGENT_STEP_LABELS[steps[1]]}`
  return `${AGENT_STEP_LABELS[steps[0]]}, ${AGENT_STEP_LABELS[steps[1]]}, and ${steps.length - 2} more`
}

export function deriveTimeHorizon(report: ChiefAnalystReport, chiefRawReport?: string): {
  horizon: string
  confidence: 'high' | 'medium' | 'low'
} {
  const corpus = `${report.catalyst} ${report.execution} ${report.tail_risk} ${chiefRawReport ?? ''}`.toLowerCase()

  if (/\b(intraday|same day|same session|today|day trade)\b/.test(corpus)) {
    return { horizon: 'Intraday (same session)', confidence: 'high' }
  }
  if (/\b(swing|next few days|next week|days to weeks|1-2 weeks|two weeks)\b/.test(corpus)) {
    return { horizon: 'Swing (2-10 trading days)', confidence: 'high' }
  }
  if (/\b(week|weeks)\b/.test(corpus)) {
    return { horizon: 'Swing (multi-week)', confidence: 'medium' }
  }
  if (/\b(month|months|quarter|long term|position)\b/.test(corpus)) {
    return { horizon: 'Position (multi-week to multi-month)', confidence: 'high' }
  }
  return { horizon: `${INSUFFICIENT_EVIDENCE} for precise horizon`, confidence: 'low' }
}

export function deriveScenarioMatrix(report: ChiefAnalystReport): ChiefScenario[] {
  return [
    {
      name: 'Bull',
      thesis: firstSentence(report.catalyst),
      trigger: report.verdict === 'BUY' ? firstSentence(report.execution) : INSUFFICIENT_EVIDENCE,
    },
    {
      name: 'Base',
      thesis: firstSentence(report.execution),
      trigger: firstSentence(report.catalyst),
    },
    {
      name: 'Bear',
      thesis: firstSentence(report.tail_risk),
      trigger: report.verdict === 'SELL' ? firstSentence(report.execution) : INSUFFICIENT_EVIDENCE,
    },
  ]
}

export function deriveSourcesSummary(reports: Partial<Record<AgentStep, string[]>>): string {
  const entries = Object.entries(reports) as [AgentStep, string[]][]
  const active = entries.filter(([, values]) => values.length > 0)
  const upstream = active.filter(([step]) => step !== 'chief_analyst')
  const notes = upstream.reduce((sum, [, values]) => sum + values.length, 0)
  const top = summarizeContributor(upstream.map(([step]) => step).slice(0, 3))

  if (upstream.length === 0) {
    return 'Sources summary: insufficient evidence from upstream analyst notes in this run.'
  }
  return `Sources summary: ${notes} upstream notes from ${upstream.length} stages, led by ${top}.`
}

export function deriveChiefReportViewModel(
  report: ChiefAnalystReport,
  reports: Partial<Record<AgentStep, string[]>>,
  chiefRawReport?: string,
): ChiefReportViewModel {
  const { horizon, confidence } = deriveTimeHorizon(report, chiefRawReport)
  return {
    timeHorizon: horizon,
    timeHorizonConfidence: confidence,
    scenarioMatrix: deriveScenarioMatrix(report),
    sourcesSummary: deriveSourcesSummary(reports),
  }
}
