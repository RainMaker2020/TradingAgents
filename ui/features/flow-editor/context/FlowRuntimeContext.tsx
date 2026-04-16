'use client'

import type { CSSProperties } from 'react'
import { createContext, useContext } from 'react'

export type FlowRuntimeValue = {
  readOnly: boolean
  patchNodeData: (nodeId: string, patch: Record<string, unknown>) => void
  /** Run detail monitor: one-time stagger delay (ms) per node id; undefined = no fade-in. */
  entranceStaggerMs?: (nodeId: string) => number | undefined
  /**
   * When entrance stagger is active, false until the first `fitView` completes so nodes stay
   * positioned before the fade-in. Ignored when `entranceStaggerMs` is unset.
   */
  entranceLayoutReady?: boolean
}

const FlowRuntimeContext = createContext<FlowRuntimeValue | null>(null)

export type MonitorEntranceFadeProps = {
  enabled: boolean
  className: string
  style: CSSProperties
}

/**
 * Returns a one-time staggered fade-in layer for the run-detail pipeline map only.
 * Editor canvas leaves `entranceStaggerMs` unset, so this is a no-op there.
 */
export function getMonitorEntranceFadeProps(
  nodeId: string,
  runtime: FlowRuntimeValue | null,
): MonitorEntranceFadeProps {
  const delayMs = runtime?.entranceStaggerMs?.(nodeId)
  if (delayMs === undefined) {
    return { enabled: false, className: '', style: {} }
  }
  if (runtime?.entranceLayoutReady === false) {
    return {
      enabled: true,
      className: 'flow-node--enter-wait',
      style: {},
    }
  }
  return {
    enabled: true,
    className: 'flow-node--enter-fade',
    style: { animationDelay: `${delayMs}ms` },
  }
}

export function FlowRuntimeProvider({
  value,
  children,
}: {
  value: FlowRuntimeValue
  children: React.ReactNode
}) {
  return <FlowRuntimeContext.Provider value={value}>{children}</FlowRuntimeContext.Provider>
}

export function useFlowRuntime(): FlowRuntimeValue | null {
  return useContext(FlowRuntimeContext)
}
