'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname } from 'next/navigation'
import { useWorkspaceRuntime } from '@/features/dashboard/hooks/useWorkspaceRuntime'
import { isAvailable, withCriticalFallback } from '@/lib/truth-state'

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
  const runtime = useWorkspaceRuntime()
  const [clockLabel, setClockLabel] = useState(currentTimeLabel)

  useEffect(() => {
    const id = setInterval(() => setClockLabel(currentTimeLabel()), 60_000)
    return () => clearInterval(id)
  }, [])

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
        {isAvailable(withCriticalFallback(runtime.apiReachable)) && (
          <div className="ws-topbar-pill">
            <span className={`ws-dot ${runtime.apiReachable.value ? 'ws-dot-buy' : 'ws-dot-sell'}`} />
            {runtime.apiReachable.value ? 'API Available' : 'API Down'}
          </div>
        )}
        {isAvailable(withCriticalFallback(runtime.sseReady)) && (
          <div className="ws-topbar-pill">
            <span className={`ws-dot ${runtime.sseReady.value ? 'ws-dot-accent' : 'ws-dot-sell'}`} />
            {runtime.sseReady.value ? 'SSE Ready' : 'SSE Down'}
          </div>
        )}
        {isAvailable(runtime.apiTarget) && (
          <div className="ws-topbar-pill">
            <span className="ws-dot ws-dot-accent" />
            {runtime.apiTarget.value}
          </div>
        )}
        <div className="ws-topbar-clock terminal-text">{clockLabel}</div>
      </div>
    </header>
  )
}
