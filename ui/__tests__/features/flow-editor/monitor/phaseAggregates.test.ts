import type { AgentStep } from '@/lib/types/run'
import { AGENT_STEPS } from '@/lib/types/run'
import {
  aggregateStepGroup,
  ANALYST_PHASE_STEPS,
  formatAggregateLine,
  RESEARCH_STEPS,
} from '@/features/flow-editor/monitor/phaseAggregates'

function allPending(): Record<AgentStep, 'pending' | 'running' | 'done'> {
  return Object.fromEntries(AGENT_STEPS.map((s) => [s, 'pending'])) as Record<
    AgentStep,
    'pending' | 'running' | 'done'
  >
}

describe('aggregateStepGroup', () => {
  it('returns pending when none have started', () => {
    const steps = allPending()
    expect(aggregateStepGroup(steps, ANALYST_PHASE_STEPS)).toBe('pending')
  })

  it('returns running when any key is running', () => {
    const steps = { ...allPending(), market_analyst: 'running' as const }
    expect(aggregateStepGroup(steps, ANALYST_PHASE_STEPS)).toBe('running')
  })

  it('returns done when all keys are done', () => {
    const steps = {
      ...allPending(),
      market_analyst: 'done' as const,
      news_analyst: 'done' as const,
      fundamentals_analyst: 'done' as const,
      social_analyst: 'done' as const,
    }
    expect(aggregateStepGroup(steps, ANALYST_PHASE_STEPS)).toBe('done')
  })
})

describe('formatAggregateLine', () => {
  it('uses in progress for a single-step group', () => {
    const steps = { ...allPending(), trader: 'running' as const }
    expect(formatAggregateLine('Trader', steps, ['trader'])).toBe('Trader · in progress')
  })

  it('names the running step for multi-step groups', () => {
    const steps = { ...allPending(), bull_researcher: 'running' as const }
    expect(formatAggregateLine('Research', steps, RESEARCH_STEPS)).toContain('Bull')
  })
})
