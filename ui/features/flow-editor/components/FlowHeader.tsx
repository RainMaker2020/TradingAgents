'use client'

type Tab = 'flow' | 'settings'

type Props = {
  active: Tab
  onChange: (t: Tab) => void
  /** Optional secondary tabs (e.g. saved flow names) rendered as pills. */
  flowTabs?: { id: string; label: string; active?: boolean }[]
  onSelectFlowTab?: (id: string) => void
}

export default function FlowHeader({ active, onChange, flowTabs, onSelectFlowTab }: Props) {
  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 px-1 py-2 border-b"
      style={{ borderColor: 'var(--border)' }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="apex-label text-[10px]" style={{ color: 'var(--accent)', opacity: 0.75 }}>
          Workspace
        </span>
        {(['flow', 'settings'] as const).map((t) => (
          <button
            key={t}
            type="button"
            className="btn-secondary !h-[32px] !px-3 !py-0 text-xs"
            style={
              active === t ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : undefined
            }
            onClick={() => onChange(t)}
          >
            {t === 'flow' ? 'Flow canvas' : 'All settings'}
          </button>
        ))}
      </div>
      {flowTabs && flowTabs.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 max-w-[min(100%,420px)]">
          {flowTabs.map((ft) => (
            <button
              key={ft.id}
              type="button"
              className="rounded-lg px-2.5 py-1 text-[10px] terminal-text truncate max-w-[140px] border transition-colors"
              style={{
                borderColor: ft.active ? 'var(--accent)' : 'var(--border-raised)',
                color: ft.active ? 'var(--accent-light)' : 'var(--text-mid)',
                background: ft.active ? 'var(--accent-glow2)' : 'transparent',
              }}
              title={ft.label}
              onClick={() => onSelectFlowTab?.(ft.id)}
            >
              {ft.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
