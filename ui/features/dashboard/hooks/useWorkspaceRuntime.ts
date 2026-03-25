'use client'

import { useEffect, useMemo, useState } from 'react'
import { getRuntimeSnapshot } from '@/lib/api-client'
import type { Settings } from '@/lib/types/settings'
import type { RuntimeConstraints, RuntimeSnapshot } from '@/lib/types/system'
import { available, type TruthValue, unknown } from '@/lib/truth-state'

let cachedSnapshot: RuntimeSnapshot | null = null
let cachedSnapshotError = false
let snapshotRequest: Promise<RuntimeSnapshot> | null = null

type WorkspaceRuntime = {
  apiReachable: TruthValue<boolean>
  sseReady: TruthValue<boolean>
  runTotals: TruthValue<{
    total: number
    running: number
    complete: number
    error: number
    queued: number
  }>
  settings: TruthValue<Settings>
  constraints: TruthValue<RuntimeConstraints>
  apiTarget: TruthValue<string>
}

function deriveApiTarget(): TruthValue<string> {
  const base = process.env.NEXT_PUBLIC_API_URL?.trim()
  if (!base) return unknown<string>()
  try {
    const url = new URL(base)
    return available(url.host)
  } catch {
    return available(base)
  }
}

export function useWorkspaceRuntime() {
  const [snapshot, setSnapshot] = useState<RuntimeSnapshot | null>(cachedSnapshot)
  const [loadError, setLoadError] = useState(cachedSnapshotError)
  const [loading, setLoading] = useState(!cachedSnapshot && !cachedSnapshotError)

  useEffect(() => {
    let active = true

    const load = snapshotRequest ?? getRuntimeSnapshot()
    if (!snapshotRequest) {
      snapshotRequest = load
    }

    load.then((runtimeSnapshot) => {
      cachedSnapshot = runtimeSnapshot
      cachedSnapshotError = false
      if (!active) return
      setSnapshot(runtimeSnapshot)
      setLoadError(false)
      setLoading(false)
    }).catch(() => {
      cachedSnapshot = null
      cachedSnapshotError = true
      if (!active) return
      setSnapshot(null)
      setLoadError(true)
      setLoading(false)
    }).finally(() => {
      snapshotRequest = null
    })

    return () => { active = false }
  }, [])

  const runtime = useMemo<WorkspaceRuntime>(() => {
    const apiReachable = (snapshot?.health.api_available && !loadError)
      ? available(snapshot.health.api_available)
      : unknown<boolean>()

    const runTotals = snapshot
      ? available({
          total: snapshot.session.total_runs,
          running: snapshot.session.running_runs,
          complete: snapshot.session.complete_runs,
          error: snapshot.session.error_runs,
          queued: snapshot.session.queued_runs,
        })
      : unknown<WorkspaceRuntime['runTotals'] extends TruthValue<infer T> ? T : never>()

    return {
      apiReachable,
      sseReady: snapshot ? available(snapshot.health.sse_supported) : unknown<boolean>(),
      runTotals,
      settings: snapshot ? available(snapshot.defaults) : unknown<Settings>(),
      constraints: snapshot ? available(snapshot.constraints) : unknown<RuntimeConstraints>(),
      apiTarget: deriveApiTarget(),
    }
  }, [snapshot, loadError])

  return { loading, ...runtime }
}
