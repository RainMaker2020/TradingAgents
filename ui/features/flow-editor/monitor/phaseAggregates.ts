import type { AgentStep } from '@/lib/types/run'
import { AGENT_STEPS, AGENT_STEP_LABELS } from '@/lib/types/run'

/** LangGraph analyst steps (four palette agents). */
export const ANALYST_PHASE_STEPS: AgentStep[] = [
  'market_analyst',
  'news_analyst',
  'fundamentals_analyst',
  'social_analyst',
]

export const RESEARCH_STEPS: AgentStep[] = ['bull_researcher', 'bear_researcher', 'research_manager']

export const RISK_DEBATE_STEPS: AgentStep[] = [
  'aggressive_analyst',
  'conservative_analyst',
  'neutral_analyst',
  'risk_judge',
]

export function aggregateStepGroup(
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>,
  keys: AgentStep[],
): 'pending' | 'running' | 'done' {
  if (keys.length === 0) return 'pending'
  const vals = keys.map((k) => steps[k])
  if (vals.some((v) => v === 'running')) return 'running'
  if (vals.every((v) => v === 'done')) return 'done'
  return 'pending'
}

/** First running step in pipeline order (for subtitles). */
export function firstRunningStepLabel(
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>,
): string | null {
  for (const s of AGENT_STEPS) {
    if (steps[s] === 'running') return AGENT_STEP_LABELS[s]
  }
  return null
}

export function doneCountInGroup(
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>,
  keys: AgentStep[],
): number {
  return keys.filter((k) => steps[k] === 'done').length
}

export function formatAggregateLine(
  label: string,
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>,
  keys: AgentStep[],
): string {
  const done = doneCountInGroup(steps, keys)
  const total = keys.length
  const running = firstRunningInKeys(steps, keys)
  if (running) {
    if (keys.length === 1) return `${label} · in progress`
    return `${label} · ${AGENT_STEP_LABELS[running]}`
  }
  if (done === total && total > 0) return `${label} · complete`
  return `${label} · ${done}/${total}`
}

function firstRunningInKeys(
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>,
  keys: AgentStep[],
): AgentStep | null {
  for (const k of keys) {
    if (steps[k] === 'running') return k
  }
  return null
}
