'use client'

import { useMemo } from 'react'
import { usePathname } from 'next/navigation'

const PAGE_LABELS: Record<string, string> = {
  '/new-run': 'Strategy Launch',
  '/history': 'Run Monitor',
  '/settings': 'Workspace Settings',
}

function currentTimeLabel() {
  return new Date().toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function GlobalTopBar() {
  const pathname = usePathname()
  const pageLabel = useMemo(() => {
    if (pathname.startsWith('/runs/')) return 'Live Run Detail'
    return PAGE_LABELS[pathname] ?? 'Trading Workspace'
  }, [pathname])

  return (
    <header className="ws-topbar">
      <div className="ws-topbar-left">
        <span className="ws-topbar-kicker">TradingAgents Terminal</span>
        <div className="ws-topbar-row">
          <span className="ws-topbar-title">Operator Workspace</span>
          <span className="ws-topbar-sep">/</span>
          <span className="ws-topbar-context">{pageLabel}</span>
        </div>
      </div>

      <div className="ws-topbar-right">
        <div className="ws-topbar-pill">
          <span className="ws-dot ws-dot-buy" />
          API Connected
        </div>
        <div className="ws-topbar-pill">
          <span className="ws-dot ws-dot-accent" />
          SSE Ready
        </div>
        <div className="ws-topbar-clock terminal-text">{currentTimeLabel()}</div>
      </div>
    </header>
  )
}
