import type { Node, Edge } from '@xyflow/react'
import type { AgentStep } from '@/lib/types/run'
import type { NewRunFormState } from '@/features/new-run/types'

/** Visual-only graph document; execution pipeline is not derived from this module. */
export type FlowEditorMode = 'edit' | 'monitor'

export type StartNodeData = {
  kind: 'start'
  ticker: string
  date: string
  mode: 'graph' | 'backtest'
  end_date: string
  deep_think_llm: string
  llm_provider: string
  /** Run detail monitor: live line from stream status. */
  monitorRunLine?: string
}

export type AgentNodeData = {
  kind: 'agent'
  analystId: string
  label: string
  status?: 'pending' | 'running' | 'done'
}

export type BacktestEngineNodeData = {
  kind: 'backtest_engine'
  status?: 'pending' | 'running' | 'done'
}

export type EndNodeData = {
  kind: 'end'
  initial_cash: number
  slippage_bps: number
  fee_per_trade: number
  max_position_pct: number
  /** Run detail monitor: chief / completion. */
  monitorOutputStatus?: 'pending' | 'running' | 'done'
  monitorOutputLine?: string
  /** Run detail monitor: show spinner until stream completes (or error). */
  monitorOutputLoading?: boolean
}

/** Architectural pipeline stages (visual; not persisted on form). */
export type PipelineStageId = 'market_data' | 'signal_strategy' | 'risk' | 'execution'

export type PipelineStageNodeData = {
  kind: 'pipeline_stage'
  stage: PipelineStageId
  /** Run detail monitor: aggregate LangGraph status for this visual stage. */
  monitorStatus?: 'pending' | 'running' | 'done'
  monitorLine?: string
}

/** Run detail monitor only: one LangGraph step in the post-analyst swimlane (non-editable). */
export type PhaseMiniNodeData = {
  kind: 'phase_mini'
  step: AgentStep
  label: string
  status?: 'pending' | 'running' | 'done'
}

export type FlowVisualNodeData =
  | StartNodeData
  | AgentNodeData
  | BacktestEngineNodeData
  | EndNodeData
  | PipelineStageNodeData
  | PhaseMiniNodeData

export type FlowVisualNode = Node<FlowVisualNodeData>

export type FlowDocument = {
  id: string
  name: string
  updatedAt: string
  /** Persisted React Flow model; optional when only `form` is stored. */
  nodes: FlowVisualNode[]
  edges: Edge[]
  viewport?: { x: number; y: number; zoom: number }
  /** Run configuration snapshot for restore (visual graph is derived via sync layer). */
  form?: NewRunFormState
}

export type FormSnapshotCallback = (snapshot: NewRunFormState) => void
