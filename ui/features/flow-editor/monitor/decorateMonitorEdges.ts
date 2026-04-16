import type { Edge } from '@xyflow/react'
import type { FlowVisualNode } from '@/features/flow-editor/types'

/** Highlight incoming edges to nodes that are currently running (live pipeline). */
export function decorateMonitorEdges(edges: Edge[], nodes: FlowVisualNode[]): Edge[] {
  const runningTargets = new Set<string>()
  for (const n of nodes) {
    if (n.type === 'agent' && n.data.kind === 'agent' && n.data.status === 'running') {
      runningTargets.add(n.id)
    }
    if (
      n.type === 'pipeline_stage' &&
      n.data.kind === 'pipeline_stage' &&
      n.data.monitorStatus === 'running'
    ) {
      runningTargets.add(n.id)
    }
    if (n.type === 'end' && n.data.kind === 'end' && n.data.monitorOutputStatus === 'running') {
      runningTargets.add(n.id)
    }
    if (
      n.type === 'backtest_engine' &&
      n.data.kind === 'backtest_engine' &&
      n.data.status === 'running'
    ) {
      runningTargets.add(n.id)
    }
    if (n.type === 'phase_mini' && n.data.kind === 'phase_mini' && n.data.status === 'running') {
      runningTargets.add(n.id)
    }
  }

  return edges.map((e) => {
    const active = runningTargets.has(e.target)
    const baseStyle = (typeof e.style === 'object' && e.style) || {}
    return {
      ...e,
      animated: active,
      style: {
        ...baseStyle,
        stroke: active ? 'var(--accent)' : 'var(--flow-edge)',
        strokeWidth: active ? 2.25 : 2,
        opacity: active ? 1 : 0.9,
      },
    }
  })
}
