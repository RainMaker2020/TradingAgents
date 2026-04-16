import dagre from '@dagrejs/dagre'
import type { Edge } from '@xyflow/react'
import type { FlowVisualNode } from '@/features/flow-editor/types'

function nodeDimensions(n: FlowVisualNode): { width: number; height: number } {
  switch (n.type) {
    case 'start':
      return { width: 260, height: 280 }
    case 'end':
      return { width: 260, height: 300 }
    case 'pipeline_stage':
      return { width: 224, height: 120 }
    case 'agent':
      return { width: 224, height: 112 }
    case 'backtest_engine':
      return { width: 224, height: 132 }
    case 'phase_mini':
      return { width: 112, height: 80 }
    default:
      return { width: 200, height: 100 }
  }
}

/**
 * Assigns left-to-right Dagre positions. Dagre uses node center (x, y); React Flow uses top-left.
 */
export function applyDagreLayout(nodes: FlowVisualNode[], edges: Edge[]): FlowVisualNode[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({
    rankdir: 'LR',
    nodesep: 72,
    ranksep: 96,
    marginx: 40,
    marginy: 40,
  })

  const idSet = new Set(nodes.map((n) => n.id))
  for (const n of nodes) {
    const { width, height } = nodeDimensions(n)
    g.setNode(n.id, { width, height })
  }

  for (const e of edges) {
    if (idSet.has(e.source) && idSet.has(e.target)) {
      g.setEdge(e.source, e.target)
    }
  }

  dagre.layout(g)

  return nodes.map((n) => {
    const laid = g.node(n.id) as { x: number; y: number; width: number; height: number } | undefined
    if (!laid) return n
    return {
      ...n,
      position: {
        x: laid.x - laid.width / 2,
        y: laid.y - laid.height / 2,
      },
    }
  })
}
