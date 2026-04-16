'use client'

import { useState } from 'react'
import { ANALYST_CATALOG } from '@/features/flow-editor/analystCatalog'

type Props = {
  disabled: boolean
}

function PaletteItem({
  title,
  subtitle,
  accent,
  onDragStart,
  disabled,
}: {
  title: string
  subtitle: string
  accent: string
  onDragStart: (e: React.DragEvent) => void
  disabled: boolean
}) {
  return (
    <div
      draggable={!disabled}
      onDragStart={disabled ? undefined : onDragStart}
      className="rounded-lg px-2.5 py-2 border cursor-grab active:cursor-grabbing"
      style={{
        borderColor: disabled ? 'var(--border)' : `${accent}40`,
        background: disabled ? 'var(--bg-elevated)' : `${accent}0C`,
        opacity: disabled ? 0.45 : 1,
      }}
    >
      <div className="text-[11px] font-semibold" style={{ color: 'var(--text-high)' }}>
        {title}
      </div>
      <div className="text-[9px] mt-0.5" style={{ color: 'var(--text-low)' }}>
        {subtitle}
      </div>
    </div>
  )
}

export default function ComponentsPalette({ disabled }: Props) {
  const [q, setQ] = useState('')
  const [openAgents, setOpenAgents] = useState(true)

  const analysts = ANALYST_CATALOG.filter(
    (a) => q.trim() === '' || a.label.toLowerCase().includes(q.trim().toLowerCase()),
  )

  return (
    <aside
      className="flex flex-col w-[240px] shrink-0 rounded-xl border overflow-hidden"
      style={{ borderColor: 'var(--border-raised)', background: 'var(--bg-sidebar)' }}
    >
      <div className="px-3 py-2.5 border-b" style={{ borderColor: 'var(--border)' }}>
        <span className="text-[11px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-mid)' }}>
          Components
        </span>
      </div>
      <div className="p-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <input
          className="vault-input terminal-text text-[11px] w-full"
          placeholder="Search components…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2 min-h-[200px]">
        <button
          type="button"
          className="w-full flex items-center justify-between text-left text-[10px] font-bold uppercase tracking-widest px-1"
          style={{ color: 'var(--accent)' }}
          onClick={() => setOpenAgents((o) => !o)}
        >
          <span>Agents</span>
          <span style={{ color: 'var(--text-low)' }}>{openAgents ? '−' : '+'}</span>
        </button>
        {openAgents && (
          <div className="space-y-1.5">
            {analysts.map((a) => (
              <PaletteItem
                key={a.id}
                title={a.short}
                subtitle="Drag onto canvas"
                accent="#A78BFA"
                disabled={disabled}
                onDragStart={(e) => {
                  e.dataTransfer.setData(
                    'application/reactflow',
                    JSON.stringify({ type: 'agent', analystId: a.id }),
                  )
                  e.dataTransfer.effectAllowed = 'move'
                }}
              />
            ))}
          </div>
        )}
        <div className="text-[9px] px-1 pt-2" style={{ color: 'var(--text-low)' }}>
          Start and output nodes are fixed in the layout; configure them on the canvas or in All settings.
        </div>
      </div>
    </aside>
  )
}
