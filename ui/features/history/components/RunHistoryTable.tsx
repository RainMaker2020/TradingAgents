'use client'
import Link from 'next/link'
import { useState, useMemo, useEffect, useLayoutEffect, useRef, useCallback } from 'react'
import type { RunSummary } from '@/lib/types/run'
import Toolbar, { ToolbarField } from '@/components/dashboard/Toolbar'
import { abortRun as apiAbortRun } from '@/lib/api-client'
import AbortConfirmModal from '@/features/run-detail/components/AbortConfirmModal'

type Props = { runs: RunSummary[]; onAbortSuccess?: () => void }

const HISTORY_FILTERS_KEY = 'ta:history-table-filters'

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const
type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

const rowActionOutlineBase = {
  display: 'inline-flex' as const,
  alignItems: 'center' as const,
  justifyContent: 'center' as const,
  background: 'transparent',
  borderRadius: '4px',
  padding: '2px 8px',
  fontSize: '11px',
  fontFamily: 'var(--font-mono)',
}

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

export default function RunHistoryTable({ runs, onAbortSuccess }: Props) {
  const [query, setQuery] = useState('')
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'BUY' | 'SELL' | 'HOLD'>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | RunSummary['status']>('all')
  const [sortBy, setSortBy] = useState<'created_desc' | 'created_asc' | 'ticker_asc'>('created_desc')
  const [abortTarget, setAbortTarget] = useState<RunSummary | null>(null)
  const [abortingIds, setAbortingIds] = useState<Set<string>>(new Set())
  const [pageSize, setPageSize] = useState<PageSize>(25)
  const [page, setPage] = useState(1)
  const skipInitialPersist = useRef(true)

  useLayoutEffect(() => {
    try {
      const raw = sessionStorage.getItem(HISTORY_FILTERS_KEY)
      if (!raw) return
      const p = JSON.parse(raw) as Record<string, unknown>
      if (typeof p.query === 'string') setQuery(p.query)
      if (p.decisionFilter === 'all' || p.decisionFilter === 'BUY' || p.decisionFilter === 'SELL' || p.decisionFilter === 'HOLD') {
        setDecisionFilter(p.decisionFilter)
      }
      const st = p.statusFilter
      if (
        st === 'all' ||
        st === 'queued' ||
        st === 'running' ||
        st === 'complete' ||
        st === 'error' ||
        st === 'aborted'
      ) {
        setStatusFilter(st)
      }
      if (p.sortBy === 'created_desc' || p.sortBy === 'created_asc' || p.sortBy === 'ticker_asc') {
        setSortBy(p.sortBy)
      }
      const ps = p.pageSize
      if (typeof ps === 'number' && PAGE_SIZE_OPTIONS.includes(ps as PageSize)) {
        setPageSize(ps as PageSize)
      }
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    if (skipInitialPersist.current) {
      skipInitialPersist.current = false
      return
    }
    try {
      sessionStorage.setItem(
        HISTORY_FILTERS_KEY,
        JSON.stringify({ query, decisionFilter, statusFilter, sortBy, pageSize }),
      )
    } catch {
      /* ignore */
    }
  }, [query, decisionFilter, statusFilter, sortBy, pageSize])

  async function handleAbortConfirm() {
    if (!abortTarget) return
    const id = abortTarget.id
    setAbortTarget(null)
    setAbortingIds((prev) => new Set(prev).add(id))
    try {
      await apiAbortRun(id)
      onAbortSuccess?.()
    } catch {
      // button re-enables via finally
    } finally {
      setAbortingIds((prev) => { const next = new Set(prev); next.delete(id); return next })
    }
  }

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

  const totalFiltered = filteredRuns.length
  const totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize))

  useEffect(() => {
    setPage(1)
  }, [query, decisionFilter, statusFilter, sortBy])

  useEffect(() => {
    setPage((p) => Math.min(p, totalPages))
  }, [totalPages])

  const paginatedRuns = useMemo(() => {
    const start = (page - 1) * pageSize
    return filteredRuns.slice(start, start + pageSize)
  }, [filteredRuns, page, pageSize])

  const rangeStart = totalFiltered === 0 ? 0 : (page - 1) * pageSize + 1
  const rangeEnd = Math.min(page * pageSize, totalFiltered)

  const goPrev = useCallback(() => setPage((p) => Math.max(1, p - 1)), [])
  const goNext = useCallback(() => setPage((p) => Math.min(totalPages, p + 1)), [totalPages])

  const pageBtnStyle = (disabled: boolean) => ({
    ...rowActionOutlineBase,
    color: disabled ? 'var(--text-low)' : 'var(--accent-light)',
    border: `1px solid ${disabled ? 'var(--border)' : 'var(--accent-light)'}`,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.45 : 1,
  })

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
                <option value="aborted">Aborted</option>
              </select>
            </ToolbarField>
          </>
        }
        right={
          <>
            <ToolbarField label="Per page">
              <select
                className="ws-control"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value) as PageSize)
                  setPage(1)
                }}
              >
                {PAGE_SIZE_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </ToolbarField>
            <ToolbarField label="Sort">
              <select className="ws-control" value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)}>
                <option value="created_desc">Newest</option>
                <option value="created_asc">Oldest</option>
                <option value="ticker_asc">Ticker A-Z</option>
              </select>
            </ToolbarField>
          </>
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
            {paginatedRuns.map((run) => (
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
                  <span className="terminal-text text-[11px]" style={{
                    color: run.status === 'error' ? 'var(--sell)'
                         : run.status === 'running' ? 'var(--hold)'
                         : run.status === 'complete' ? 'var(--buy)'
                         : run.status === 'aborted' ? 'var(--text-low)'
                         : 'var(--text-low)'
                  }}>
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
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Link
                      href={`/runs/${run.id}`}
                      className="ws-table-action"
                      style={{
                        ...rowActionOutlineBase,
                        color: 'var(--accent-light)',
                        border: '1px solid var(--accent-light)',
                        cursor: 'pointer',
                        textDecoration: 'none',
                      }}
                    >
                      Open
                    </Link>
                    {(run.status === 'queued' || run.status === 'running') && (
                      <button
                        type="button"
                        onClick={() => setAbortTarget(run)}
                        disabled={abortingIds.has(run.id)}
                        style={{
                          ...rowActionOutlineBase,
                          color: 'var(--error)',
                          border: '1px solid var(--error)',
                          cursor: abortingIds.has(run.id) ? 'not-allowed' : 'pointer',
                          opacity: abortingIds.has(run.id) ? 0.5 : 1,
                        }}
                      >
                        {abortingIds.has(run.id) ? '…' : 'Abort'}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {totalFiltered === 0 && (
              <tr>
                <td colSpan={6} className="terminal-text text-xs" style={{ color: 'var(--text-low)' }}>
                  No rows match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <span className="terminal-text text-[10px]" style={{ color: 'var(--text-low)' }}>
          {totalFiltered === 0
            ? `0 / ${runs.length} VISIBLE`
            : `${rangeStart}–${rangeEnd} of ${totalFiltered} · ${runs.length} total`}
        </span>
        <div className="flex items-center gap-2">
          <span className="terminal-text text-[10px]" style={{ color: 'var(--text-low)' }}>
            PAGE {page} / {totalPages}
          </span>
          <button type="button" onClick={goPrev} disabled={page <= 1} style={pageBtnStyle(page <= 1)}>
            Prev
          </button>
          <button type="button" onClick={goNext} disabled={page >= totalPages} style={pageBtnStyle(page >= totalPages)}>
            Next
          </button>
        </div>
        <span className="terminal-text text-[10px] shrink-0" style={{ color: 'var(--text-low)' }}>
          DESKTOP MONITOR MODE
        </span>
      </div>

      <AbortConfirmModal
        open={abortTarget !== null}
        ticker={abortTarget?.ticker ?? ''}
        onConfirm={handleAbortConfirm}
        onCancel={() => setAbortTarget(null)}
      />
    </div>
  )
}
