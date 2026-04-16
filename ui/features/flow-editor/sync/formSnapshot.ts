import type { Edge } from '@xyflow/react'
import type { NewRunFormState } from '@/features/new-run/types'
import { analystLabel } from '@/features/flow-editor/analystCatalog'
import type { FlowVisualNode, PipelineStageId } from '@/features/flow-editor/types'

const START_ID = 'node-start'
const END_ID = 'node-end'
const BT_ID = 'node-backtest-engine'

export const MARKET_ID = 'node-pipeline-market'
export const SIGNAL_ID = 'node-pipeline-signal'
export const RISK_ID = 'node-pipeline-risk'
export const EXEC_ID = 'node-pipeline-execution'

/** Left-to-right columns (px). */
const X = {
  start: 32,
  market: 252,
  signal: 472,
  agents: 692,
  backtest: 692,
  risk: 948,
  exec: 1172,
  end: 1396,
} as const

const ROW_GAP = 92
const AGENT_TOP = 56

function spineY(agentCount: number): number {
  if (agentCount <= 0) return 232
  return AGENT_TOP + ((agentCount - 1) * ROW_GAP) / 2
}

function agentY(index: number): number {
  return AGENT_TOP + index * ROW_GAP
}

function pipelineNode(
  id: string,
  stage: PipelineStageId,
  position: { x: number; y: number },
): FlowVisualNode {
  return {
    id,
    type: 'pipeline_stage',
    position,
    data: { kind: 'pipeline_stage', stage },
  }
}

function edge(id: string, source: string, target: string): Edge {
  return { id, source, target, type: 'smoothstep', animated: false }
}

/** Derive edges from current node list (handles palette drops before form sync). */
export function edgesFromNodes(nodes: FlowVisualNode[]): Edge[] {
  const hasBt = nodes.some((n) => n.id === BT_ID)
  const agents = nodes.filter((n) => n.type === 'agent')

  const trunk: Edge[] = [edge('e-s-m', START_ID, MARKET_ID), edge('e-m-sig', MARKET_ID, SIGNAL_ID)]

  if (hasBt) {
    return [
      ...trunk,
      edge('e-sig-bt', SIGNAL_ID, BT_ID),
      edge('e-bt-r', BT_ID, RISK_ID),
      edge('e-r-ex', RISK_ID, EXEC_ID),
      edge('e-ex-end', EXEC_ID, END_ID),
    ]
  }

  if (agents.length === 0) {
    return [
      ...trunk,
      edge('e-sig-r', SIGNAL_ID, RISK_ID),
      edge('e-r-ex', RISK_ID, EXEC_ID),
      edge('e-ex-end', EXEC_ID, END_ID),
    ]
  }

  const fan = agents.flatMap((an) => [
    edge(`e-${SIGNAL_ID}-${an.id}`, SIGNAL_ID, an.id),
    edge(`e-${an.id}-${RISK_ID}`, an.id, RISK_ID),
  ])

  return [...trunk, ...fan, edge('e-r-ex', RISK_ID, EXEC_ID), edge('e-ex-end', EXEC_ID, END_ID)]
}

function clampPositions(nodes: FlowVisualNode[]): Map<string, { x: number; y: number }> {
  const m = new Map<string, { x: number; y: number }>()
  for (const n of nodes) {
    m.set(n.id, { ...n.position })
  }
  return m
}

/** Build graph nodes/edges from form; preserves prior node positions when IDs match. */
export function formToVisualGraph(
  form: NewRunFormState,
  previousNodes: FlowVisualNode[],
): { nodes: FlowVisualNode[]; edges: Edge[] } {
  const prev = clampPositions(previousNodes)

  const analysts = form.mode === 'graph' ? form.enabled_analysts : []
  const n = analysts.length
  const centerY = spineY(n)

  const startPos = prev.get(START_ID) ?? { x: X.start, y: centerY }
  const endPos = prev.get(END_ID) ?? { x: X.end, y: centerY }

  const start: FlowVisualNode = {
    id: START_ID,
    type: 'start',
    position: startPos,
    data: {
      kind: 'start',
      ticker: form.ticker,
      date: form.date,
      mode: form.mode,
      end_date: form.end_date,
      deep_think_llm: form.deep_think_llm,
      llm_provider: form.llm_provider,
    },
  }

  const end: FlowVisualNode = {
    id: END_ID,
    type: 'end',
    position: endPos,
    data: {
      kind: 'end',
      initial_cash: form.initial_cash,
      slippage_bps: form.slippage_bps,
      fee_per_trade: form.fee_per_trade,
      max_position_pct: form.max_position_pct,
    },
  }

  const market = pipelineNode(
    MARKET_ID,
    'market_data',
    prev.get(MARKET_ID) ?? { x: X.market, y: centerY },
  )
  const signal = pipelineNode(
    SIGNAL_ID,
    'signal_strategy',
    prev.get(SIGNAL_ID) ?? { x: X.signal, y: centerY },
  )
  const risk = pipelineNode(RISK_ID, 'risk', prev.get(RISK_ID) ?? { x: X.risk, y: centerY })
  const exec = pipelineNode(EXEC_ID, 'execution', prev.get(EXEC_ID) ?? { x: X.exec, y: centerY })

  if (form.mode === 'backtest') {
    const btPos = prev.get(BT_ID) ?? { x: X.backtest, y: centerY }
    const bt: FlowVisualNode = {
      id: BT_ID,
      type: 'backtest_engine',
      position: btPos,
      data: { kind: 'backtest_engine' },
    }
    const nodes: FlowVisualNode[] = [start, end, market, signal, bt, risk, exec]
    return { nodes, edges: edgesFromNodes(nodes) }
  }

  const agentNodes: FlowVisualNode[] = analysts.map((aid, i) => {
    const id = `node-agent-${aid}`
    const pos = prev.get(id) ?? { x: X.agents, y: agentY(i) }
    return {
      id,
      type: 'agent',
      position: pos,
      data: { kind: 'agent', analystId: aid, label: analystLabel(aid) },
    }
  })

  const nodes: FlowVisualNode[] = [start, end, market, signal, ...agentNodes, risk, exec]
  return { nodes, edges: edgesFromNodes(nodes) }
}

/** Merge visual node data into an existing form snapshot (graph structure is canonical from form for agents). */
export function visualGraphToForm(form: NewRunFormState, nodes: FlowVisualNode[]): NewRunFormState {
  let next: NewRunFormState = { ...form }

  for (const n of nodes) {
    if (n.type === 'start' && n.data.kind === 'start') {
      const d = n.data
      next = {
        ...next,
        ticker: d.ticker,
        date: d.date,
        mode: d.mode,
        end_date: d.end_date,
        deep_think_llm: d.deep_think_llm,
        llm_provider: d.llm_provider,
      }
    }
    if (n.type === 'end' && n.data.kind === 'end') {
      const d = n.data
      next = {
        ...next,
        initial_cash: d.initial_cash,
        slippage_bps: d.slippage_bps,
        fee_per_trade: d.fee_per_trade,
        max_position_pct: d.max_position_pct,
      }
    }
  }

  const agentIds = nodes
    .filter((n) => n.type === 'agent' && n.data.kind === 'agent')
    .map((n) => (n.data as { analystId: string }).analystId)

  if (next.mode === 'graph') {
    next = { ...next, enabled_analysts: [...new Set(agentIds)] }
  }

  return next
}

export const FLOW_NODE_IDS = {
  START_ID,
  END_ID,
  BT_ID,
  MARKET_ID,
  SIGNAL_ID,
  RISK_ID,
  EXEC_ID,
} as const
