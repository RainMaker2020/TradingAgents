'use client'

import RunConfigForm from '@/features/new-run/components/RunConfigForm'
import MetricStrip from '@/components/dashboard/MetricStrip'
import Panel from '@/components/dashboard/Panel'
import { useWorkspaceRuntime } from '@/features/dashboard/hooks/useWorkspaceRuntime'
import { AGENT_STEPS, STEP_PHASE } from '@/lib/types/run'
import { DEFAULT_FORM } from '@/features/new-run/types'
import { isAvailable } from '@/lib/truth-state'

export default function NewRunPage() {
  const runtime = useWorkspaceRuntime()
  const phaseCount = new Set(AGENT_STEPS.map((step) => STEP_PHASE[step])).size
  const analystsEnabled = DEFAULT_FORM.enabled_analysts.length

  return (
    <>
      <div className="ws-page-header">
        <div>
          <div className="apex-label" style={{ color: 'var(--accent)', opacity: 0.8 }}>
            Strategy Launch
          </div>
          <h1 className="ws-page-title">New Analysis Run</h1>
          <p className="ws-page-subtitle">
            Configure a multi-agent run, validate model inputs, and launch with trading-desk controls.
          </p>
        </div>
      </div>

      <MetricStrip
        items={[
          { label: 'Pipeline Phases', value: String(phaseCount), tone: 'accent' },
          { label: 'Analysts Enabled', value: String(analystsEnabled), tone: 'positive' },
          {
            label: 'Default Debate',
            value: isAvailable(runtime.settings)
              ? `${runtime.settings.value.max_debate_rounds} Round`
              : 'N/A',
            tone: 'warning',
          },
          { label: 'Run ETA', value: 'Unknown', tone: 'neutral' },
        ]}
      />

      <div className="ws-grid-2 animate-fade-up">
        <RunConfigForm />

        <div className="space-y-3">
          <Panel title="Execution Flow" subtitle="What happens after launch">
            <ol className="space-y-2">
              {[
                'Analysts ingest market, news, fundamentals, and social signals.',
                'Research agents run bull/bear synthesis and manager consensus.',
                'Trader and risk committee process position and risk posture.',
                'Chief analyst publishes final BUY/SELL/HOLD verdict.',
              ].map((line, idx) => (
                <li key={line} className="flex gap-2.5">
                  <span
                    className="terminal-text text-[10px] pt-0.5"
                    style={{ color: 'var(--accent-light)', minWidth: '22px' }}
                  >
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                  <span className="text-[13px]" style={{ color: 'var(--text-mid)' }}>
                    {line}
                  </span>
                </li>
              ))}
            </ol>
          </Panel>

          <Panel title="Operator Guidance" subtitle="Pre-launch checks">
            <ul className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
              <li>Confirm ticker/date pair reflects the trading session under review.</li>
              <li>Use higher-capacity model for deep reasoning on volatile symbols.</li>
              <li>Increase debate rounds only when thesis conflict is expected.</li>
              <li>Keep social analyst enabled for momentum-sensitive equities.</li>
            </ul>
          </Panel>
        </div>
      </div>
    </>
  )
}
