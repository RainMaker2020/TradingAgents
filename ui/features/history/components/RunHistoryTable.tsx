import Link from 'next/link'
import { useMemo, useState } from 'react'
import type { RunSummary } from '@/lib/types/run'
import Toolbar, { ToolbarField } from '@/components/dashboard/Toolbar'

type Props = { runs: RunSummary[] }

function DecisionBadge({ decision }: { decision: string }) {
  const lower = decision.toLowerCase()
  if (lower === 'buy')  return <span className="badge-buy">{decision}</span>
  if (lower === 'sell') return <span className="badge-sell">{decision}</span>
  if (lower === 'hold') return <span className="badge-hold">{decision}</span>
  return (
    <span
      className="px-2.5 py-1 rounded-full text-[10px] font-bold"
      style={{
        fontFamily: 'var(--font-mono)',
        letterSpacing: '0.08em',
        background: 'var(--bg-elevated)',
        color: 'var(--text-mid)',
        border: '1px solid var(--border-raised)',
      }}
    >
      {decision}
    </span>
  )
}

function StatusDot({ decision }: { decision?: string }) {
  const lower = decision?.toLowerCase()
  const color = lower === 'buy' ? 'var(--buy)' : lower === 'sell' ? 'var(--sell)' : lower === 'hold' ? 'var(--hold)' : 'var(--text-low)'
  return (
    <div
      className="w-1.5 h-1.5 rounded-full shrink-0"
      style={{ background: color, boxShadow: decision ? `0 0 5px ${color}80` : 'none' }}
    />
  )
}

export default function RunHistoryTable({ runs }: Props) {
  const [query, setQuery] = useState('')
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'BUY' | 'SELL' | 'HOLD'>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | RunSummary['status']>('all')
  const [sortBy, setSortBy] = useState<'created_desc' | 'created_asc' | 'ticker_asc'>('created_desc')

  const filteredRuns = useMemo(() => {
    const searched = runs.filter((run) => {
      const hitTicker = run.ticker.toLowerCase().includes(query.toLowerCase())
      const hitDate = run.date.includes(query)
      const matchDecision = decisionFilter === 'all' || run.decision === decisionFilter
      const matchStatus = statusFilter === 'all' || run.status === statusFilter
      return (hitTicker || hitDate) && matchDecision && matchStatus
    })

    if (sortBy === 'ticker_asc') {
      return [...searched].sort((a, b) => a.ticker.localeCompare(b.ticker))
    }
    if (sortBy === 'created_asc') {
      return [...searched].sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at))
    }
    return [...searched].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
  }, [runs, query, decisionFilter, statusFilter, sortBy])

  if (runs.length === 0) {
    return (
      <div
        className="rounded-2xl flex flex-col items-center justify-center py-20 gap-4"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        {/* Empty state icon */}
        <div
          className="w-14 h-14 rounded-2xl flex items-center justify-center"
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-raised)' }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="4" rx="2" fill="var(--text-low)"/>
            <rect x="3" y="10" width="12" height="4" rx="2" fill="var(--text-low)" opacity=".6"/>
            <rect x="3" y="17" width="15" height="4" rx="2" fill="var(--text-low)" opacity=".4"/>
          </svg>
        </div>
        <div className="text-center">
          <p
            className="text-sm font-medium mb-1"
            style={{ color: 'var(--text-mid)', fontFamily: 'var(--font-manrope)' }}
          >
            No analysis runs yet
          </p>
          <p className="text-xs" style={{ color: 'var(--text-low)' }}>
            Start your first analysis to see results here
          </p>
        </div>
        <Link href="/new-run" className="btn-primary mt-2">
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
            <polygon points="2.5,2 9,5.5 2.5,9" fill="currentColor"/>
          </svg>
          New Analysis
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <Toolbar
        left={
          <>
            <ToolbarField label="Search">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="ws-control terminal-text w-[180px]"
                placeholder="Ticker or date"
              />
            </ToolbarField>
            <ToolbarField label="Decision">
              <select className="ws-control" value={decisionFilter} onChange={(e) => setDecisionFilter(e.target.value as typeof decisionFilter)}>
                <option value="all">All</option>
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
                <option value="HOLD">HOLD</option>
              </select>
            </ToolbarField>
            <ToolbarField label="Status">
              <select className="ws-control" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}>
                <option value="all">All</option>
                <option value="queued">Queued</option>
                <option value="running">Running</option>
                <option value="complete">Complete</option>
                <option value="error">Error</option>
              </select>
            </ToolbarField>
          </>
        }
        right={
          <ToolbarField label="Sort">
            <select className="ws-control" value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)}>
              <option value="created_desc">Newest</option>
              <option value="created_asc">Oldest</option>
              <option value="ticker_asc">Ticker A-Z</option>
            </select>
          </ToolbarField>
        }
      />

      <div className="overflow-hidden rounded-xl" style={{ border: '1px solid var(--border)' }}>
        <table className="ws-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Date</th>
              <th>Status</th>
              <th>Decision</th>
              <th>Created</th>
              <th aria-label="Action" />
            </tr>
          </thead>
          <tbody>
            {filteredRuns.map((run) => (
              <tr key={run.id}>
                <td>
                  <div className="flex items-center gap-2">
                    <StatusDot decision={run.decision ?? undefined} />
                    <span className="terminal-text font-bold text-sm" style={{ color: 'var(--text-high)' }}>
                      {run.ticker}
                    </span>
                  </div>
                </td>
                <td className="terminal-text">{run.date}</td>
                <td>
                  <span className="terminal-text text-[11px]" style={{ color: run.status === 'error' ? 'var(--sell)' : run.status === 'running' ? 'var(--hold)' : run.status === 'complete' ? 'var(--buy)' : 'var(--text-low)' }}>
                    {run.status.toUpperCase()}
                  </span>
                </td>
                <td>
                  {run.decision ? (
                    <DecisionBadge decision={run.decision} />
                  ) : (
                    <span className="terminal-text text-[11px]" style={{ color: 'var(--text-low)' }}>
                      PENDING
                    </span>
                  )}
                </td>
                <td className="terminal-text text-xs">{new Date(run.created_at).toLocaleString()}</td>
                <td>
                  <Link href={`/runs/${run.id}`} className="ws-table-action">
                    Open
                  </Link>
                </td>
              </tr>
            ))}
            {filteredRuns.length === 0 && (
              <tr>
                <td colSpan={6} className="terminal-text text-xs" style={{ color: 'var(--text-low)' }}>
                  No rows match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between px-1">
        <span className="terminal-text text-[10px]" style={{ color: 'var(--text-low)' }}>
          {filteredRuns.length} / {runs.length} VISIBLE
        </span>
        <span className="terminal-text text-[10px]" style={{ color: 'var(--text-low)' }}>
          DESKTOP MONITOR MODE
        </span>
      </div>
    </div>
  )
}
