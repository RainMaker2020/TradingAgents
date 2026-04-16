import type { CSSProperties } from 'react'
import type { Edge } from '@xyflow/react'
import type { AgentStep } from '@/lib/types/run'
import { AGENT_STEP_LABELS } from '@/lib/types/run'
import type { FlowVisualNode } from '@/features/flow-editor/types'
import { edgesFromNodes, FLOW_NODE_IDS } from '@/features/flow-editor/sync/formSnapshot'

const { SIGNAL_ID, END_ID } = FLOW_NODE_IDS

/** LangGraph order after the four analysts (matches streamed `steps` keys). */
export const POST_ANALYST_CHAIN: AgentStep[] = [
  'bull_researcher',
  'bear_researcher',
  'research_manager',
  'trader',
  'aggressive_analyst',
  'conservative_analyst',
  'neutral_analyst',
  'risk_judge',
  'chief_analyst',
]

export function phaseMiniNodeId(step: AgentStep): string {
  return `node-phase-mini-${step}`
}

function maxNodeBottomY(nodes: FlowVisualNode[]): number {
  let max = 0
  for (const n of nodes) {
    max = Math.max(max, n.position.y)
  }
  return max
}

/** Second swimlane below the main topology; preserves prior positions when IDs match. */
export function buildPhaseSwimlaneNodes(
  baseNodes: FlowVisualNode[],
  prevPhasePositions: Map<string, { x: number; y: number }>,
): FlowVisualNode[] {
  const swimlaneY = maxNodeBottomY(baseNodes) + 200
  const gap = 122
  const x0 = 28

  return POST_ANALYST_CHAIN.map((step, i) => {
    const id = phaseMiniNodeId(step)
    const pos = prevPhasePositions.get(id) ?? { x: x0 + i * gap, y: swimlaneY }
    return {
      id,
      type: 'phase_mini',
      position: pos,
      draggable: false,
      selectable: false,
      data: {
        kind: 'phase_mini',
        step,
        label: AGENT_STEP_LABELS[step],
      },
    } as FlowVisualNode
  })
}

function edge(id: string, source: string, target: string, style?: CSSProperties): Edge {
  return { id, source, target, type: 'smoothstep', animated: false, style }
}

/** Main graph edges plus sequential swimlane edges and bridges (run monitor only). */
export function buildMonitorEdges(mainNodes: FlowVisualNode[]): Edge[] {
  const main = mainNodes.filter((n) => n.type !== 'phase_mini')
  const inner = edgesFromNodes(main)

  const chain: Edge[] = []
  for (let i = 1; i < POST_ANALYST_CHAIN.length; i++) {
    const a = POST_ANALYST_CHAIN[i - 1]
    const b = POST_ANALYST_CHAIN[i]
    chain.push(
      edge(`e-phase-seq-${a}-${b}`, phaseMiniNodeId(a), phaseMiniNodeId(b), {
        stroke: 'var(--flow-edge)',
        strokeWidth: 1.75,
        opacity: 0.92,
      }),
    )
  }

  const bridge: Edge[] = [
    edge(
      'e-mon-signal-bull',
      SIGNAL_ID,
      phaseMiniNodeId('bull_researcher'),
      { strokeDasharray: '6 4', stroke: 'var(--text-mid)', strokeWidth: 1.5, opacity: 0.75 },
    ),
    edge(
      'e-mon-chief-end',
      phaseMiniNodeId('chief_analyst'),
      END_ID,
      { strokeDasharray: '6 4', stroke: 'var(--text-mid)', strokeWidth: 1.5, opacity: 0.75 },
    ),
  ]

  return [...inner, ...chain, ...bridge]
}
