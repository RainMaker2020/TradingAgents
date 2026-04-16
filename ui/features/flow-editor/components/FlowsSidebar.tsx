'use client'

import { useEffect, useMemo, useState } from 'react'
import type { FlowDocument } from '@/features/flow-editor/types'
import { loadFlowDocuments } from '@/features/flow-editor/storage/flowStorage'

type Props = {
  onLoad: (doc: FlowDocument) => void
  onSave: (name: string) => void
}

export default function FlowsSidebar({ onLoad, onSave }: Props) {
  const [query, setQuery] = useState('')
  const [name, setName] = useState('')
  /** Avoid reading localStorage during render — SSR and client must match on first paint. */
  const [hydrationSafe, setHydrationSafe] = useState(false)
  const [flows, setFlows] = useState<FlowDocument[]>([])

  useEffect(() => {
    setFlows(loadFlowDocuments())
    setHydrationSafe(true)
  }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return flows
    return flows.filter((f) => f.name.toLowerCase().includes(q))
  }, [flows, query])

  return (
    <aside
      className="flex flex-col w-[240px] shrink-0 rounded-xl border overflow-hidden"
      style={{ borderColor: 'var(--border-raised)', background: 'var(--bg-sidebar)' }}
    >
      <div className="px-3 py-2.5 border-b flex items-center justify-between gap-2" style={{ borderColor: 'var(--border)' }}>
        <span className="text-[11px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-mid)' }}>
          Flows
        </span>
        <div className="flex gap-1">
          <button
            type="button"
            className="btn-secondary !h-[26px] !px-2 !text-[10px]"
            onClick={() => {
              const n = name.trim() || `Flow ${new Date().toLocaleString()}`
              onSave(n)
            }}
          >
            Save
          </button>
        </div>
      </div>
      <div className="p-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <input
          className="vault-input terminal-text text-[11px] w-full"
          placeholder="Save as…"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="p-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <input
          className="vault-input terminal-text text-[11px] w-full"
          placeholder="Search flows…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1 min-h-[200px]">
        <div className="text-[9px] uppercase tracking-wider mb-1" style={{ color: 'var(--text-low)' }}>
          Recent
        </div>
        {!hydrationSafe ? (
          <p className="text-[11px] px-1 py-2" style={{ color: 'var(--text-low)' }}>
            Loading saved flows…
          </p>
        ) : (
          <>
            {filtered.length === 0 && (
              <p className="text-[11px] px-1 py-2" style={{ color: 'var(--text-low)' }}>
                No saved flows yet. Name a snapshot and press Save.
              </p>
            )}
            {filtered.map((f) => (
              <button
                key={f.id}
                type="button"
                className="w-full text-left rounded-lg px-2 py-2 border transition-colors"
                style={{
                  borderColor: 'var(--border)',
                  background: 'var(--bg-elevated)',
                }}
                onClick={() => onLoad(f)}
              >
                <div className="text-[12px] font-semibold truncate" style={{ color: 'var(--text-high)' }}>
                  {f.name}
                </div>
                <div className="text-[9px] terminal-text mt-0.5" style={{ color: 'var(--text-low)' }}>
                  {new Date(f.updatedAt).toLocaleString()}
                </div>
              </button>
            ))}
          </>
        )}
      </div>
    </aside>
  )
}
