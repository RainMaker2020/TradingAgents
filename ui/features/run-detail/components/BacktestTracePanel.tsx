'use client'

import { useMemo, useState } from 'react'
import type { BacktestTraceEvent } from '@/lib/types/run'
import { summarizeBacktestEvent, traceRowTone } from '@/lib/backtestTrace'

const TONE_COLOR: Record<string, string> = {
  buy: 'var(--buy)',
  sell: 'var(--sell)',
  hold: 'var(--hold)',
  warn: 'var(--accent-light)',
  muted: 'var(--text-low)',
}

type Props = {
  events: BacktestTraceEvent[]
}

function formatTs(iso: string | undefined): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
  } catch {
    return iso
  }
}

export default function BacktestTracePanel({ events }: Props) {
  const [rawOpen, setRawOpen] = useState(false)

  const rows = useMemo(
    () =>
      events.map((ev, i) => ({
        i,
        ev,
        summary: summarizeBacktestEvent(ev),
        tone: traceRowTone(ev),
      })),
    [events],
  )

  if (events.length === 0) return null

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] terminal-text uppercase tracking-widest" style={{ color: 'var(--text-low)' }}>
          Simulation timeline · {events.length} events
        </p>
        <label className="flex items-center gap-2 cursor-pointer terminal-text text-[11px]" style={{ color: 'var(--text-mid)' }}>
          <input
            type="checkbox"
            checked={rawOpen}
            onChange={(e) => setRawOpen(e.target.checked)}
            className="rounded border"
            style={{ borderColor: 'var(--border)' }}
          />
          Show raw JSON
        </label>
      </div>

      <div className="overflow-x-auto rounded-xl" style={{ border: '1px solid var(--border)' }}>
        <table className="ws-table text-[12px]">
          <thead>
            <tr>
              <th className="w-10">#</th>
              <th>Type</th>
              <th>Time (UTC)</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ i, ev, summary, tone }) => (
              <tr key={`${i}-${ev.timestamp ?? i}`}>
                <td className="terminal-text" style={{ color: 'var(--text-low)' }}>
                  {i + 1}
                </td>
                <td>
                  <span
                    className="terminal-text text-[10px] font-bold uppercase tracking-wide"
                    style={{ color: TONE_COLOR[tone] ?? 'var(--text-mid)' }}
                  >
                    {ev.event_type ?? 'UNKNOWN'}
                  </span>
                </td>
                <td className="terminal-text whitespace-nowrap" style={{ color: 'var(--text-mid)' }}>
                  {formatTs(ev.timestamp)}
                </td>
                <td>
                  <div className="terminal-text leading-snug" style={{ color: 'var(--text-high)' }}>
                    {summary}
                  </div>
                  {rawOpen && (
                    <pre
                      className="mt-2 text-[10px] whitespace-pre-wrap break-all max-h-40 overflow-y-auto p-2 rounded-lg"
                      style={{
                        background: 'var(--bg-elevated)',
                        color: 'var(--text-mid)',
                        fontFamily: 'var(--font-mono)',
                        border: '1px solid var(--border-raised)',
                      }}
                    >
                      {JSON.stringify(ev, null, 2)}
                    </pre>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-low)' }}>
        Each row is one engine step: data availability, LangGraph signal (BUY/SELL/HOLD and reasoning when
        present), risk/execution outcomes, and fills at next-session open. This complements the aggregate
        metrics above—it does not replace per-agent LLM transcripts (graph mode only).
      </p>
    </div>
  )
}
