'use client'
import { use, useMemo, useState } from 'react'
import { useRunStream } from '@/features/run-detail/hooks/useRunStream'
import PipelineStepper from '@/features/run-detail/components/PipelineStepper'
import VerdictBanner from '@/features/run-detail/components/VerdictBanner'
import PhaseTabs from '@/features/run-detail/components/PhaseTabs'
import TokenStatsBar from '@/features/run-detail/components/TokenStatsBar'
import ChiefAnalystCard from '@/features/run-detail/components/ChiefAnalystCard'
import MetricStrip from '@/components/dashboard/MetricStrip'
import Panel from '@/components/dashboard/Panel'
import Toolbar, { ToolbarField } from '@/components/dashboard/Toolbar'
import { AGENT_STEP_LABELS } from '@/lib/types/run'
import type { AgentStep } from '@/lib/types/run'

const STATUS_CONFIG: Record<string, {
  bg: string; color: string; dot: string; label: string; pulse: boolean
}> = {
  connecting: { bg: 'var(--bg-elevated)',     color: 'var(--text-mid)',  dot: 'var(--text-low)',  label: 'Connecting',  pulse: false },
  running:    { bg: 'var(--hold-bg)',          color: 'var(--hold)',      dot: 'var(--hold)',      label: 'Running',     pulse: true  },
  complete:   { bg: 'var(--buy-bg)',           color: 'var(--buy)',       dot: 'var(--buy)',       label: 'Complete',    pulse: false },
  error:      { bg: 'var(--error-bg)',         color: 'var(--error)',     dot: 'var(--error)',     label: 'Error',       pulse: false },
}

export default function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { steps, reports, verdict, status, error, tokensTotal, tokensByStep, chiefAnalystReport, ticker, date } = useRunStream(id)
  const [viewMode, setViewMode] = useState<'overview' | 'diagnostics'>('overview')

  const sc = STATUS_CONFIG[status] ?? STATUS_CONFIG.connecting
  const stepEntries = Object.entries(steps)
  const completedSteps = stepEntries.filter(([, value]) => value === 'done').length
  const runningSteps = stepEntries.filter(([, value]) => value === 'running').length

  const highestTokenStep = useMemo(() => {
    const leader = Object.entries(tokensByStep).sort((a, b) => {
      const aTotal = a[1].in + a[1].out
      const bTotal = b[1].in + b[1].out
      return bTotal - aTotal
    })[0]

    if (!leader || leader[1].in + leader[1].out === 0) return 'N/A'
    return AGENT_STEP_LABELS[leader[0] as AgentStep] ?? leader[0].replace(/_/g, ' ')
  }, [tokensByStep])

  return (
    <div className="space-y-4 animate-fade-up">
      <div className="ws-page-header">
        <div>
          <div className="apex-label mb-2" style={{ color: 'var(--accent)', opacity: 0.7 }}>
            Live Execution
          </div>
          <h1 className="ws-page-title">
            {ticker ? (
              <>
                <span className="terminal-text" style={{ color: 'var(--accent-light)' }}>{ticker}</span>
                <span style={{ margin: '0 10px', color: 'var(--text-low)' }}>·</span>
                <span className="terminal-text text-[22px]" style={{ color: 'var(--text-mid)' }}>{date}</span>
              </>
            ) : (
              'Loading run'
            )}
          </h1>
        </div>
        <div
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-full text-[10px] font-bold mt-1.5 shrink-0"
          style={{
            background: sc.bg,
            color: sc.color,
            border: `1px solid ${sc.dot}40`,
            fontFamily: 'var(--font-mono)',
            letterSpacing: '0.1em',
          }}
        >
          <div
            className="w-1.5 h-1.5 rounded-full shrink-0"
            style={{
              background: sc.dot,
              boxShadow: sc.pulse ? `0 0 6px ${sc.dot}` : 'none',
              animation: sc.pulse ? 'shimmer 1s ease-in-out infinite' : 'none',
            }}
          />
          {sc.label.toUpperCase()}
        </div>
      </div>

      <MetricStrip
        items={[
          { label: 'Completed Steps', value: `${completedSteps}/${stepEntries.length}`, tone: 'positive' },
          { label: 'Running Steps', value: String(runningSteps), tone: 'warning' },
          { label: 'Token In / Out', value: `${tokensTotal.in} / ${tokensTotal.out}`, tone: 'accent' },
          { label: 'Top Token Agent', value: highestTokenStep, tone: 'neutral' },
        ]}
      />

      <Toolbar
        left={
          <ToolbarField label="View">
            {(['overview', 'diagnostics'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                className="btn-secondary !h-[34px] !px-3 !py-0 text-xs"
                style={viewMode === mode ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : undefined}
                onClick={() => setViewMode(mode)}
              >
                {mode === 'overview' ? 'Overview' : 'Diagnostics'}
              </button>
            ))}
          </ToolbarField>
        }
        right={
          <span className="terminal-text text-[10px]" style={{ color: 'var(--text-low)', letterSpacing: '0.08em' }}>
            RUN ID · {id.slice(0, 8)}
          </span>
        }
      />

      <div className="ws-grid-2">
        <div className="space-y-4 min-w-0">
          {/* Token stats bar */}
          <TokenStatsBar tokensTotal={tokensTotal} />

          {/* Chief Analyst Executive Summary */}
          <ChiefAnalystCard
            report={chiefAnalystReport}
            status={steps['chief_analyst']}
            ticker={ticker ?? ''}
            date={date ?? ''}
          />

          {/* Pipeline */}
          <PipelineStepper steps={steps} />

          {/* Error */}
          {error && (
            <div
              className="px-4 py-3 rounded-xl text-sm flex items-center gap-2"
              style={{
                background: 'var(--error-bg)',
                color: 'var(--error)',
                border: '1px solid rgba(255,43,62,0.25)',
              }}
            >
              <span className="font-bold">Error:</span> {error}
            </div>
          )}

          {/* Verdict */}
          {verdict && ticker && date && (
            <VerdictBanner verdict={verdict} ticker={ticker} date={date} />
          )}

          {/* Phase tabs + reports */}
          <PhaseTabs steps={steps} reports={reports} tokensByStep={tokensByStep} />
        </div>

        <div className="space-y-3">
          <Panel title="Live Operations" subtitle="Run health and execution state">
            <div className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
              <div className="flex items-center justify-between">
                <span>Status</span>
                <span className="terminal-text" style={{ color: sc.color }}>{sc.label.toUpperCase()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Steps completed</span>
                <span className="terminal-text">{completedSteps}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Steps running</span>
                <span className="terminal-text">{runningSteps}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Total output tokens</span>
                <span className="terminal-text">{tokensTotal.out}</span>
              </div>
            </div>
          </Panel>

          <Panel title="Workflow Guidance" subtitle="Operator checklist">
            <ul className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
              <li>Track pipeline completion before reading final verdict confidence.</li>
              <li>Use diagnostics view to inspect token-intensive agent stages.</li>
              <li>Escalate if any step remains running abnormally long.</li>
              <li>Compare verdict with per-phase reports before execution decisions.</li>
            </ul>
          </Panel>

          {viewMode === 'diagnostics' && (
            <Panel title="Token Diagnostics" subtitle="Per-step usage sample">
              <div className="space-y-1.5">
                {Object.entries(tokensByStep)
                  .filter(([, usage]) => usage.in + usage.out > 0)
                  .sort((a, b) => (b[1].in + b[1].out) - (a[1].in + a[1].out))
                  .slice(0, 6)
                  .map(([step, usage]) => (
                    <div key={step} className="flex items-center justify-between text-[11px]">
                      <span style={{ color: 'var(--text-mid)' }} className="terminal-text">
                        {step}
                      </span>
                      <span style={{ color: 'var(--text-high)' }} className="terminal-text">
                        {usage.in + usage.out}
                      </span>
                    </div>
                  ))}
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  )
}
