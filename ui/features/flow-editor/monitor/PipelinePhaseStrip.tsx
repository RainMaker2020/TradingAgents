'use client'

import type { AgentStep } from '@/lib/types/run'
import {
  aggregateStepGroup,
  ANALYST_PHASE_STEPS,
  RESEARCH_STEPS,
  RISK_DEBATE_STEPS,
} from '@/features/flow-editor/monitor/phaseAggregates'

const PHASES: { key: string; label: string; steps: AgentStep[] }[] = [
  { key: 'analysts', label: 'Analysts', steps: ANALYST_PHASE_STEPS },
  { key: 'research', label: 'Research', steps: RESEARCH_STEPS },
  { key: 'trader', label: 'Trader', steps: ['trader'] },
  { key: 'risk', label: 'Risk', steps: RISK_DEBATE_STEPS },
  { key: 'chief', label: 'Chief', steps: ['chief_analyst'] },
]

function chipTone(st: 'pending' | 'running' | 'done'): { fg: string; bg: string; border: string } {
  if (st === 'running') {
    return { fg: 'var(--hold)', bg: 'var(--hold-bg)', border: 'var(--hold)' }
  }
  if (st === 'done') {
    return { fg: 'var(--accent-light)', bg: 'var(--bg-card)', border: 'var(--accent)' }
  }
  return { fg: 'var(--text-mid)', bg: 'var(--bg-card)', border: 'var(--border)' }
}

function chipLabel(st: 'pending' | 'running' | 'done'): string {
  if (st === 'running') return 'Active'
  if (st === 'done') return 'Done'
  return '—'
}

type Props = {
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>
}

/** Full LangGraph phase coverage — complements the four analyst nodes on the canvas. */
export default function PipelinePhaseStrip({ steps }: Props) {
  return (
    <div
      className="mt-2 flex flex-wrap items-center gap-2 px-0.5"
      role="status"
      aria-label="LangGraph phase status"
    >
      <span className="text-[9px] terminal-text uppercase tracking-wider" style={{ color: 'var(--text-low)' }}>
        Phases
      </span>
      {PHASES.map(({ key, label, steps: keys }) => {
        const st = aggregateStepGroup(steps, keys)
        const tone = chipTone(st)
        return (
          <span
            key={key}
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[9px] font-bold terminal-text border transition-colors duration-200"
            style={{
              color: tone.fg,
              background: tone.bg,
              borderColor: `${tone.border}55`,
            }}
          >
            <span>{label}</span>
            <span className="opacity-90" style={{ fontWeight: 600 }}>
              {chipLabel(st)}
            </span>
          </span>
        )
      })}
    </div>
  )
}
