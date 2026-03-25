'use client'
import Link from 'next/link'
import { useRunHistory } from '@/features/history/hooks/useRunHistory'
import RunHistoryTable from '@/features/history/components/RunHistoryTable'
import MetricStrip from '@/components/dashboard/MetricStrip'
import Panel from '@/components/dashboard/Panel'

export default function HistoryPage() {
  const { runs, loading, error } = useRunHistory()

  return (
    <>
      <div className="ws-page-header">
        <div>
          <div className="apex-label" style={{ color: 'var(--accent)', opacity: 0.7 }}>
            Monitoring Desk
          </div>
          <h1 className="ws-page-title">Run History</h1>
          <p className="ws-page-subtitle">Filter and inspect prior agent executions with a scan-first operations table.</p>
        </div>

        <Link href="/new-run" className="btn-primary shrink-0">
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
            <polygon points="2.5,2 9,5.5 2.5,9" fill="var(--bg-base)"/>
          </svg>
          New Analysis
        </Link>
      </div>

      <MetricStrip
        items={[
          { label: 'Total Runs', value: String(runs.length), tone: 'accent' },
          { label: 'Completed', value: String(runs.filter((r) => r.status === 'complete').length), tone: 'positive' },
          { label: 'Running', value: String(runs.filter((r) => r.status === 'running').length), tone: 'warning' },
          { label: 'Errors', value: String(runs.filter((r) => r.status === 'error').length), tone: 'negative' },
        ]}
      />

      {loading && (
        <div className="flex items-center gap-2.5 py-8" style={{ color: 'var(--text-mid)' }}>
          <div
            className="w-2 h-2 rounded-full"
            style={{ background: 'var(--accent)', animation: 'shimmer 1s infinite' }}
          />
          <span className="text-sm" style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', letterSpacing: '0.04em' }}>
            Loading runs…
          </span>
        </div>
      )}

      {error && (
        <div
          className="px-4 py-3 rounded-xl text-sm"
          style={{
            background: 'var(--error-bg)',
            color: 'var(--error)',
            border: '1px solid rgba(255,43,62,0.25)',
          }}
        >
          {error}
        </div>
      )}

      {!loading && !error && (
        <Panel title="Execution Log" subtitle="All runs · sortable and filterable">
          <RunHistoryTable runs={runs} />
        </Panel>
      )}
    </>
  )
}
