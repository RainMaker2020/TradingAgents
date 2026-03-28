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
    // Only block the page on the first load. Background refetches keep the table mounted
    // so client state (filters, etc.) is not lost after abort or refresh.
    if (tick === 0) setLoading(true)
    listRuns()
      .then((data) => {
        setRuns(data)
        setError(null)
      })
      .catch((e) => setError(e.message))
      .finally(() => {
        if (tick === 0) setLoading(false)
      })
  }, [tick])

  const refresh = useCallback(() => setTick((t) => t + 1), [])

  return { runs, loading, error, refresh }
}
