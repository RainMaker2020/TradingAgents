import type { Edge } from '@xyflow/react'
import { decorateMonitorEdges } from '@/features/flow-editor/monitor/decorateMonitorEdges'
import type { FlowVisualNode } from '@/features/flow-editor/types'

describe('decorateMonitorEdges', () => {
  it('animates edges whose target node is running', () => {
    const edges: Edge[] = [
      { id: 'e1', source: 'a', target: 'b', type: 'smoothstep' },
    ]
    const nodes = [
      {
        id: 'b',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: { kind: 'agent' as const, analystId: 'market', label: 'M', status: 'running' as const },
      },
    ] as FlowVisualNode[]

    const out = decorateMonitorEdges(edges, nodes)
    expect(out[0]?.animated).toBe(true)
    expect(out[0]?.style).toMatchObject({ stroke: 'var(--accent)' })
  })

  it('does not animate when no running targets', () => {
    const edges: Edge[] = [{ id: 'e1', source: 'a', target: 'b', type: 'smoothstep' }]
    const nodes = [
      {
        id: 'b',
        type: 'agent',
        position: { x: 0, y: 0 },
        data: { kind: 'agent' as const, analystId: 'market', label: 'M', status: 'pending' as const },
      },
    ] as FlowVisualNode[]

    const out = decorateMonitorEdges(edges, nodes)
    expect(out[0]?.animated).toBe(false)
  })
})
