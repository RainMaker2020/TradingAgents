import { buildMonitorEdges, buildPhaseSwimlaneNodes, phaseMiniNodeId, POST_ANALYST_CHAIN } from '@/features/flow-editor/monitor/buildPhaseSwimlane'
import { formToVisualGraph } from '@/features/flow-editor/sync/formSnapshot'
import { DEFAULT_FORM } from '@/features/new-run/types'

describe('buildPhaseSwimlane', () => {
  it('creates one mini-node per post-analyst step', () => {
    const { nodes: base } = formToVisualGraph(DEFAULT_FORM, [])
    const swim = buildPhaseSwimlaneNodes(base, new Map())
    expect(swim).toHaveLength(POST_ANALYST_CHAIN.length)
    expect(swim[0]?.id).toBe(phaseMiniNodeId('bull_researcher'))
    expect(swim[POST_ANALYST_CHAIN.length - 1]?.id).toBe(phaseMiniNodeId('chief_analyst'))
  })

  it('buildMonitorEdges includes swimlane chain and bridges', () => {
    const { nodes: base } = formToVisualGraph(DEFAULT_FORM, [])
    const swim = buildPhaseSwimlaneNodes(base, new Map())
    const all = [...base, ...swim]
    const edges = buildMonitorEdges(all)
    const ids = new Set(edges.map((e) => e.id))
    expect(ids.has('e-mon-signal-bull')).toBe(true)
    expect(ids.has('e-mon-chief-end')).toBe(true)
    expect(ids.has(`e-phase-seq-bull_researcher-bear_researcher`)).toBe(true)
  })
})
