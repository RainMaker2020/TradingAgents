'use client'
import { useMemo, useState } from 'react'
import { AGENT_STEPS, STEP_PHASE } from '@/lib/types/run'
import type { AgentStep } from '@/lib/types/run'
import type { StepStatus } from '@/lib/types/agents'
import AnalystReports from './AnalystReports'

type Phase = 'analysts' | 'researchers' | 'trader' | 'risk' | 'summary'

const TABS: { label: string; phase: Phase }[] = [
  { label: 'Analysts', phase: 'analysts' },
  { label: 'Researchers', phase: 'researchers' },
  { label: 'Trader', phase: 'trader' },
  { label: 'Risk', phase: 'risk' },
  { label: 'Chief Analyst', phase: 'summary' },
]

type Props = {
  steps:        Record<AgentStep, StepStatus>
  reports:      Record<AgentStep, string[]>
  tokensByStep: Record<AgentStep, { in: number; out: number }>
}

function getPhaseCompletion(phase: Phase, steps: Record<AgentStep, StepStatus>): number {
  const phaseSteps = AGENT_STEPS.filter((s) => STEP_PHASE[s] === phase)
  const done = phaseSteps.filter((s) => steps[s as AgentStep] === 'done').length
  return phaseSteps.length > 0 ? Math.round((done / phaseSteps.length) * 100) : 0
}

function getPhaseStatus(phase: Phase, steps: Record<AgentStep, StepStatus>): 'done' | 'running' | 'pending' {
  const phaseSteps = AGENT_STEPS.filter((s) => STEP_PHASE[s] === phase)
  if (phaseSteps.every((s) => steps[s as AgentStep] === 'done')) return 'done'
  if (phaseSteps.some((s) => steps[s as AgentStep] === 'running')) return 'running'
  return 'pending'
}

export default function PhaseTabs({ steps, reports, tokensByStep }: Props) {
  const [active, setActive] = useState<Phase>('analysts')
  const phaseCounts = useMemo(() => {
    return TABS.reduce<Record<Phase, number>>((acc, tab) => {
      acc[tab.phase] = AGENT_STEPS.filter((s) => STEP_PHASE[s] === tab.phase).length
      return acc
    }, { analysts: 0, researchers: 0, trader: 0, risk: 0, summary: 0 })
  }, [])

  return (
    <div>
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <div className="apex-label">Agent Reports</div>
        <div
          className="text-[10px] font-medium"
          style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-low)', letterSpacing: '0.06em' }}
        >
          {TABS.filter((t) => getPhaseCompletion(t.phase, steps) === 100).length} / {TABS.length} COMPLETE
        </div>
      </div>

      {/* Tab bar */}
      <div
        className="flex gap-1 p-1 mb-5"
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          width: 'fit-content',
        }}
      >
        {TABS.map(({ label, phase }) => {
          const isActive  = active === phase
          const status    = getPhaseStatus(phase, steps)
          const isDone    = status === 'done'
          const isRunning = status === 'running'

          return (
            <button
              key={phase}
              onClick={() => setActive(phase)}
              className="relative flex items-center gap-2 px-4 py-1.5 rounded-lg text-[13px] font-medium transition-all duration-150"
              style={
                isActive
                  ? {
                      background: 'var(--bg-elevated)',
                      color: 'var(--text-high)',
                      border: '1px solid var(--border-active)',
                      fontFamily: 'var(--font-manrope)',
                      boxShadow: '0 1px 8px rgba(0,0,0,0.3)',
                    }
                  : {
                      color: 'var(--text-mid)',
                      fontFamily: 'var(--font-manrope)',
                    }
              }
            >
              {/* Status indicator */}
              {isDone && (
                <div
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: 'var(--buy)' }}
                />
              )}
              {isRunning && (
                <div
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: 'var(--status-running)', animation: 'shimmer 1s infinite' }}
                />
              )}

              {label}

              {/* Agent count */}
              <span
                className="px-1.5 rounded text-[9px] font-bold"
                style={{
                  fontFamily: 'var(--font-mono)',
                  background: isActive ? 'var(--accent-glow)' : 'var(--bg-elevated)',
                  color: isActive ? 'var(--accent)' : 'var(--text-low)',
                  letterSpacing: '0.05em',
                }}
              >
                {phaseCounts[phase]}
              </span>
            </button>
          )
        })}
      </div>

      {/* Reports */}
      <AnalystReports phase={active} steps={steps} reports={reports} tokensByStep={tokensByStep} />
    </div>
  )
}
