'use client'
import { use, useMemo, useState } from 'react'
import { useRunStream } from '@/features/run-detail/hooks/useRunStream'
import PipelineStepper from '@/features/run-detail/components/PipelineStepper'
import VerdictBanner from '@/features/run-detail/components/VerdictBanner'
import PhaseTabs from '@/features/run-detail/components/PhaseTabs'
import TokenStatsBar from '@/features/run-detail/components/TokenStatsBar'
import ChiefAnalystCard from '@/features/run-detail/components/ChiefAnalystCard'
import AbortConfirmModal from '@/features/run-detail/components/AbortConfirmModal'
import BacktestTracePanel from '@/features/run-detail/components/BacktestTracePanel'
import MetricStrip from '@/components/dashboard/MetricStrip'
import Panel from '@/components/dashboard/Panel'
import Toolbar, { ToolbarField } from '@/components/dashboard/Toolbar'
import { deriveBacktestHeadlineFromMetrics } from '@/lib/backtestHeadline'
import {
  OPERATOR_GUIDANCE_POST_BACKTEST,
  OPERATOR_GUIDANCE_POST_GRAPH,
} from '@/lib/runModeSidebarCopy'
import { AGENT_STEP_LABELS } from '@/lib/types/run'
import type { AgentStep, BacktestTerminalExposure } from '@/lib/types/run'

const STATUS_CONFIG: Record<string, {
  bg: string; color: string; dot: string; label: string; pulse: boolean
}> = {
  connecting: { bg: 'var(--bg-elevated)',     color: 'var(--text-mid)',  dot: 'var(--text-low)',  label: 'Connecting',  pulse: false },
  running:    { bg: 'var(--hold-bg)',          color: 'var(--hold)',      dot: 'var(--hold)',      label: 'Running',     pulse: true  },
  complete:   { bg: 'var(--buy-bg)',           color: 'var(--buy)',       dot: 'var(--buy)',       label: 'Complete',    pulse: false },
  error:      { bg: 'var(--error-bg)',         color: 'var(--error)',     dot: 'var(--error)',     label: 'Error',       pulse: false },
}

function formatMoney(v: number): string {
  const abs = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return v < 0 ? `-$${abs}` : `$${abs}`
}

function formatPct(v: number | null): string {
  if (v === null) return 'N/A'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

function formatTerminalExposure(e: BacktestTerminalExposure): string {
  if (e === 'long') return 'Open long'
  if (e === 'flat_closed') return 'Flat (after trades)'
  return 'Flat (no trades)'
}

function formatAsOfUtc(iso: string | null): string {
  if (!iso) return 'N/A'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return `${d.toISOString().slice(0, 19).replace('T', ' ')} UTC`
  } catch {
    return iso
  }
}

export default function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const {
    steps,
    reports,
    verdict,
    status,
    error,
    tokensTotal,
    tokensByStep,
    chiefAnalystReport,
    ticker,
    date,
    mode,
    endDate,
    backtestSummary,
    backtestHeadline,
    backtestMetrics,
    backtestTrace,
    llmProvider,
    deepThinkLlm,
    quickThinkLlm,
    abortRun,
    isAborting,
  } = useRunStream(id)
  const [viewMode, setViewMode] = useState<'overview' | 'diagnostics'>('overview')
  const [showAbortModal, setShowAbortModal] = useState(false)

  const sc = STATUS_CONFIG[status] ?? STATUS_CONFIG.connecting
  const isBacktest = mode === 'backtest'
  const isRunning = status === 'running' || status === 'connecting'
  const stepEntries = Object.entries(steps)
  const completedSteps = stepEntries.filter(([, value]) => value === 'done').length
  const runningSteps = stepEntries.filter(([, value]) => value === 'running').length
  const chiefReports = reports['chief_analyst'] ?? []
  const chiefRawReport = chiefReports[chiefReports.length - 1]

  const highestTokenStep = useMemo(() => {
    const leader = Object.entries(tokensByStep).sort((a, b) => {
      const aTotal = a[1].in + a[1].out
      const bTotal = b[1].in + b[1].out
      return bTotal - aTotal
    })[0]

    if (!leader || leader[1].in + leader[1].out === 0) return 'N/A'
    return AGENT_STEP_LABELS[leader[0] as AgentStep] ?? leader[0].replace(/_/g, ' ')
  }, [tokensByStep])
  const modeLabel = mode === 'backtest' ? 'BACKTEST' : mode === 'graph' ? 'GRAPH' : 'UNKNOWN'
  const modeTone = mode === 'backtest' ? 'var(--hold)' : 'var(--accent)'
  const dateLabel = isBacktest && date && endDate ? `${date} → ${endDate}` : date
  const viewModes = ['overview', 'diagnostics'] as const
  const runContextLabel = isBacktest ? 'Backtest simulation' : 'Live execution'

  const scanHeadline = useMemo(() => {
    if (backtestHeadline) return backtestHeadline
    if (backtestMetrics && ticker && date) {
      return deriveBacktestHeadlineFromMetrics(ticker, date, endDate, backtestMetrics)
    }
    return null
  }, [backtestHeadline, backtestMetrics, ticker, date, endDate])

  const metricItems = isBacktest
    ? backtestMetrics
      ? [
          { label: 'Final Equity',   value: formatMoney(backtestMetrics.final_equity),     tone: 'accent' as const },
          {
            label: 'Total Return',
            value: formatPct(backtestMetrics.total_return_pct),
            tone:
              backtestMetrics.total_return_pct === null
                ? ('neutral' as const)
                : backtestMetrics.total_return_pct > 0
                  ? ('positive' as const)
                  : backtestMetrics.total_return_pct < 0
                    ? ('negative' as const)
                    : ('neutral' as const),
          },
          { label: 'Realized P&L',   value: formatMoney(backtestMetrics.realized_pnl),     tone: backtestMetrics.realized_pnl > 0 ? 'positive' as const : backtestMetrics.realized_pnl < 0 ? 'negative' as const : 'neutral' as const },
          { label: 'Unrealized P&L', value: formatMoney(backtestMetrics.unrealized_pnl),   tone: backtestMetrics.unrealized_pnl > 0 ? 'positive' as const : backtestMetrics.unrealized_pnl < 0 ? 'negative' as const : 'neutral' as const },
          { label: 'Fills',          value: String(backtestMetrics.fill_count),             tone: 'neutral' as const },
          {
            label: 'At end',
            value: formatTerminalExposure(backtestMetrics.terminal_exposure),
            tone: 'neutral' as const,
          },
          { label: 'Fees Paid',      value: formatMoney(backtestMetrics.total_fees_paid),   tone: 'warning' as const },
          {
            label: 'Max drawdown',
            value: formatPct(backtestMetrics.max_drawdown_pct),
            tone:
              backtestMetrics.max_drawdown_pct === null
                ? ('neutral' as const)
                : backtestMetrics.max_drawdown_pct < 0
                  ? ('negative' as const)
                  : ('neutral' as const),
          },
          { label: 'Metrics as-of', value: formatAsOfUtc(backtestMetrics.as_of), tone: 'neutral' as const },
        ]
      : [
          { label: 'Execution Mode', value: modeLabel, tone: 'warning' as const },
          { label: 'Run Status',     value: sc.label.toUpperCase(), tone: 'neutral' as const },
          { label: 'Summary',        value: backtestSummary ? 'READY' : isRunning ? 'PENDING' : 'UNAVAILABLE', tone: 'accent' as const },
          { label: 'Abort',          value: isRunning ? (isAborting ? 'STOPPING' : 'AVAILABLE') : 'N/A', tone: 'neutral' as const },
        ]
    : [
        { label: 'Completed Steps', value: `${completedSteps}/${stepEntries.length}`, tone: 'positive' as const },
        { label: 'Running Steps', value: String(runningSteps), tone: 'warning' as const },
        { label: 'Token In / Out', value: `${tokensTotal.in} / ${tokensTotal.out}`, tone: 'accent' as const },
        { label: 'Top Token Agent', value: highestTokenStep, tone: 'neutral' as const },
      ]

  return (
    <div className="space-y-4 animate-fade-up">
      <div className="ws-page-header">
        <div>
          <div className="apex-label mb-2" style={{ color: 'var(--accent)', opacity: 0.7 }}>
            {runContextLabel}
          </div>
          <h1 className="ws-page-title">
            {ticker ? (
              <>
                <span className="terminal-text" style={{ color: 'var(--accent-light)' }}>{ticker}</span>
                <span style={{ margin: '0 10px', color: 'var(--text-low)' }}>·</span>
                <span className="terminal-text text-[22px]" style={{ color: 'var(--text-mid)' }}>{dateLabel}</span>
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
          <span
            className="px-1.5 py-0.5 rounded"
            style={{
              background: `${modeTone}18`,
              color: modeTone,
              border: `1px solid ${modeTone}40`,
            }}
          >
            {modeLabel}
          </span>
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

      <MetricStrip items={metricItems} />

      <Toolbar
        left={
          <ToolbarField label="View">
            {viewModes.map((mode) => (
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
          <div className="flex items-center gap-2 flex-wrap justify-end">
            {isBacktest && (backtestMetrics != null || (backtestTrace != null && backtestTrace.length > 0)) && (
              <button
                type="button"
                className="btn-secondary !h-[34px] !px-3 !py-0 text-xs"
                onClick={() => {
                  const payload = {
                    run_id: id,
                    ticker,
                    date,
                    end_date: endDate,
                    mode: 'backtest' as const,
                    metrics: backtestMetrics,
                    trace: backtestTrace ?? [],
                    summary_text: backtestSummary,
                  }
                  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `backtest-${id.slice(0, 8)}.json`
                  a.click()
                  URL.revokeObjectURL(url)
                }}
              >
                Export JSON
              </button>
            )}
            <span className="terminal-text text-[10px]" style={{ color: 'var(--text-low)', letterSpacing: '0.08em' }}>
              RUN ID · {id.slice(0, 8)}
            </span>
            {isRunning && (
              <button
                type="button"
                className="btn-secondary !h-[34px] !px-3 !py-0 text-xs"
                style={{ borderColor: 'rgba(255,43,62,0.35)', color: 'var(--error)' }}
                onClick={() => setShowAbortModal(true)}
                disabled={isAborting}
              >
                {isAborting ? 'Stopping...' : 'Abort Run'}
              </button>
            )}
          </div>
        }
      />

      <div className="ws-grid-2">
        <div className="space-y-4 min-w-0">
          {/* Token stats: graph mode streams per-step; backtest embeds LLM totals in metrics. */}
          {((!isBacktest && (tokensTotal.in > 0 || tokensTotal.out > 0)) ||
            (isBacktest && backtestMetrics && (backtestMetrics.llm_tokens_in > 0 || backtestMetrics.llm_tokens_out > 0))) && (
            <TokenStatsBar
              tokensTotal={
                isBacktest && backtestMetrics
                  ? { in: backtestMetrics.llm_tokens_in, out: backtestMetrics.llm_tokens_out }
                  : tokensTotal
              }
            />
          )}

          {/* Chief Analyst Executive Summary */}
          {mode !== 'backtest' && (
            <ChiefAnalystCard
              report={chiefAnalystReport}
              status={steps['chief_analyst']}
              ticker={ticker ?? ''}
              date={date ?? ''}
              reports={reports}
              chiefRawReport={chiefRawReport}
            />
          )}

          {mode === 'backtest' && (scanHeadline || backtestSummary) && (
            <Panel
              title="Backtest result"
              subtitle={
                scanHeadline
                  ? 'Scan line is generated from the same metrics as the tiles (server or client fallback).'
                  : 'Engine text output'
              }
            >
              {scanHeadline && (
                <p
                  className="text-[15px] leading-snug mb-4 terminal-text font-medium tracking-tight"
                  style={{ color: 'var(--text-high)' }}
                >
                  {scanHeadline}
                </p>
              )}
              {backtestSummary && (
                <details className="group">
                  <summary
                    className="cursor-pointer terminal-text text-[11px] font-bold uppercase tracking-widest list-none flex items-center gap-2"
                    style={{ color: 'var(--accent)' }}
                  >
                    <span aria-hidden className="inline-block transition-transform group-open:rotate-90" style={{ color: 'var(--text-low)' }}>▸</span>
                    Full engine output
                  </summary>
                  <pre
                    className="text-[12px] whitespace-pre-wrap mt-3 pl-1 border-l-2"
                    style={{
                      color: 'var(--text-mid)',
                      fontFamily: 'var(--font-mono)',
                      borderColor: 'var(--border)',
                    }}
                  >
                    {backtestSummary}
                  </pre>
                </details>
              )}
            </Panel>
          )}

          {mode === 'backtest' && backtestTrace && backtestTrace.length > 0 && (
            <Panel
              title="Simulation timeline"
              subtitle="Per-bar events: data, LangGraph signal, risk, execution (next-open fills)."
            >
              <BacktestTracePanel events={backtestTrace} />
            </Panel>
          )}

          {mode === 'backtest' && !scanHeadline && !backtestSummary && isRunning && (
            <Panel title="Backtest In Progress" subtitle="Engine status">
              <div className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
                <p>
                  Backtest is running. Summary and metrics appear after the engine completes.
                </p>
                <p>
                  Current status: <span className="terminal-text" style={{ color: sc.color }}>{sc.label.toUpperCase()}</span>
                </p>
              </div>
            </Panel>
          )}

          {/* Pipeline */}
          {mode !== 'backtest' && <PipelineStepper steps={steps} />}

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
            <VerdictBanner
              verdict={verdict}
              ticker={ticker}
              date={date}
              mode={mode}
              endDate={endDate}
            />
          )}

          {/* Phase tabs + reports */}
          {mode !== 'backtest' && (
            <PhaseTabs steps={steps} reports={reports} tokensByStep={tokensByStep} />
          )}
        </div>

        <div className="space-y-3">
          <Panel title="Live Operations" subtitle="Run health and execution state">
            <div className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
              <div className="flex items-center justify-between">
                <span>Status</span>
                <span className="terminal-text" style={{ color: sc.color }}>{sc.label.toUpperCase()}</span>
              </div>
              <div className="flex items-start justify-between gap-3">
                <span className="shrink-0">LLM provider</span>
                <span className="terminal-text text-right break-all text-[11px]" style={{ color: 'var(--text-high)' }} title={llmProvider ?? undefined}>
                  {llmProvider ?? '—'}
                </span>
              </div>
              <div className="flex items-start justify-between gap-3">
                <span className="shrink-0">Deep think</span>
                <span className="terminal-text text-right break-all text-[11px]" style={{ color: 'var(--text-high)' }} title={deepThinkLlm ?? undefined}>
                  {deepThinkLlm ?? '—'}
                </span>
              </div>
              <div className="flex items-start justify-between gap-3">
                <span className="shrink-0">Quick think</span>
                <span className="terminal-text text-right break-all text-[11px]" style={{ color: 'var(--text-high)' }} title={quickThinkLlm ?? undefined}>
                  {quickThinkLlm ?? '—'}
                </span>
              </div>
              {isBacktest ? (
                <>
                  <div className="flex items-center justify-between">
                    <span>Backtest summary</span>
                    <span className="terminal-text">{backtestSummary ? 'READY' : 'PENDING'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Abort control</span>
                    <span className="terminal-text">{isRunning ? (isAborting ? 'STOPPING' : 'AVAILABLE') : 'N/A'}</span>
                  </div>
                </>
              ) : (
                <>
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
                </>
              )}
            </div>
          </Panel>

          <Panel
            title="Operator Guidance"
            subtitle={
              isBacktest
                ? 'Backtest (Engine) · post-run checklist'
                : 'Graph (LLM) · post-run checklist'
            }
          >
            <ul className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
              {(isBacktest ? OPERATOR_GUIDANCE_POST_BACKTEST : OPERATOR_GUIDANCE_POST_GRAPH).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </Panel>

          {viewMode === 'diagnostics' && isBacktest && (
            <Panel title="Backtest diagnostics" subtitle="LLM usage · graph-style step breakdown is N/A here">
              <div className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
                <p>
                  LangGraph ran inside the engine for each bar (minus signal-cache hits). Aggregate token counts
                  are on the metrics payload and in the token bar when non-zero.
                </p>
                {backtestMetrics && (
                  <div className="flex flex-wrap gap-x-4 gap-y-1 terminal-text text-[11px]">
                    <span>
                      LLM in: <span style={{ color: 'var(--text-high)' }}>{backtestMetrics.llm_tokens_in}</span>
                    </span>
                    <span>
                      LLM out: <span style={{ color: 'var(--text-high)' }}>{backtestMetrics.llm_tokens_out}</span>
                    </span>
                  </div>
                )}
                <p className="text-[11px]" style={{ color: 'var(--text-low)' }}>
                  Data source path and loaded bar date range are appended to the full engine output (Overview).
                </p>
              </div>
            </Panel>
          )}
          {viewMode === 'diagnostics' && !isBacktest && (
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
      <AbortConfirmModal
        open={showAbortModal}
        ticker={ticker ?? 'this'}
        onCancel={() => setShowAbortModal(false)}
        onConfirm={() => {
          setShowAbortModal(false)
          void abortRun()
        }}
      />
    </div>
  )
}
