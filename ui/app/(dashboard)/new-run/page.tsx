'use client'

import { useState } from 'react'
import RunConfigForm from '@/features/new-run/components/RunConfigForm'
import MetricStrip from '@/components/dashboard/MetricStrip'
import Panel from '@/components/dashboard/Panel'
import { useWorkspaceRuntime } from '@/features/dashboard/hooks/useWorkspaceRuntime'
import { AGENT_STEPS, STEP_PHASE } from '@/lib/types/run'
import { DEFAULT_FORM } from '@/features/new-run/types'
import { isAvailable } from '@/lib/truth-state'
import {
  EXECUTION_FLOW_BACKTEST,
  EXECUTION_FLOW_GRAPH,
  OPERATOR_GUIDANCE_PRE_BACKTEST,
  OPERATOR_GUIDANCE_PRE_GRAPH,
} from '@/lib/runModeSidebarCopy'

export default function NewRunPage() {
  const [executionMode, setExecutionMode] = useState<'graph' | 'backtest'>('graph')
  const runtime = useWorkspaceRuntime()
  const phaseCount = new Set(AGENT_STEPS.map((step) => STEP_PHASE[step])).size
  const analystsEnabled = DEFAULT_FORM.enabled_analysts.length

  const metricItems =
    executionMode === 'backtest'
      ? [
          { label: 'Run mode', value: 'Backtest (Engine)', tone: 'accent' as const },
          { label: 'Engine', value: 'Bar loop + sim', tone: 'positive' as const },
          {
            label: 'Workspace default',
            value: isAvailable(runtime.settings)
              ? runtime.settings.value.execution_mode === 'backtest'
                ? 'Engine'
                : 'Graph'
              : 'N/A',
            tone: 'warning' as const,
          },
          { label: 'Run ETA', value: 'Unknown', tone: 'neutral' as const },
        ]
      : [
          { label: 'Run mode', value: 'Graph (LLM)', tone: 'accent' as const },
          { label: 'Pipeline phases', value: String(phaseCount), tone: 'positive' as const },
          { label: 'Analysts enabled', value: String(analystsEnabled), tone: 'positive' as const },
          {
            label: 'Default debate',
            value: isAvailable(runtime.settings)
              ? `${runtime.settings.value.max_debate_rounds} rnd`
              : 'N/A',
            tone: 'warning' as const,
          },
          { label: 'Run ETA', value: 'Unknown', tone: 'neutral' as const },
        ]

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

      <MetricStrip items={metricItems} />

      <div className="ws-grid-2 animate-fade-up">
        <RunConfigForm onExecutionModeChange={setExecutionMode} />

        <div className="space-y-3">
          <Panel
            title="Execution Flow"
            subtitle={
              executionMode === 'backtest'
                ? 'Backtest (Engine) · what happens after launch'
                : 'Graph (LLM) · what happens after launch'
            }
          >
            <ol className="space-y-2">
              {(executionMode === 'backtest' ? EXECUTION_FLOW_BACKTEST : EXECUTION_FLOW_GRAPH).map((line, idx) => (
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

          <Panel
            title="Operator Guidance"
            subtitle={
              executionMode === 'backtest'
                ? 'Backtest (Engine) · pre-launch checks'
                : 'Graph (LLM) · pre-launch checks'
            }
          >
            <ul className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
              {(executionMode === 'backtest' ? OPERATOR_GUIDANCE_PRE_BACKTEST : OPERATOR_GUIDANCE_PRE_GRAPH).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>
    </>
  )
}
