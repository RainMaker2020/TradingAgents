'use client'
import { useCallback, useEffect, useState } from 'react'
import { listRuns } from '@/lib/api-client'
import type { RunSummary } from '@/lib/types/run'

export function useRunHistory() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    setLoading(true)
    listRuns()
      .then(setRuns)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [tick])

  const refresh = useCallback(() => setTick((t) => t + 1), [])

  return { runs, loading, error, refresh }
}
