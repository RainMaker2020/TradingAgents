'use client'

import { useEffect, useMemo, useState } from 'react'
import { useNodesState } from '@xyflow/react'
import type { AgentStep, RunStatus } from '@/lib/types/run'
import type { NewRunFormState } from '@/features/new-run/types'
import { buildMonitorEdges, buildPhaseSwimlaneNodes } from '@/features/flow-editor/monitor/buildPhaseSwimlane'
import { FLOW_NODE_IDS, formToVisualGraph } from '@/features/flow-editor/sync/formSnapshot'
import type { FlowVisualNode } from '@/features/flow-editor/types'
import { stepStatusForAnalyst } from '@/features/flow-editor/monitor/analystStepMap'
import FlowCanvas from '@/features/flow-editor/components/FlowCanvas'
import { applyDagreLayout } from '@/features/flow-editor/layout/applyDagreLayout'
import { decorateMonitorEdges } from '@/features/flow-editor/monitor/decorateMonitorEdges'
import PipelinePhaseStrip from '@/features/flow-editor/monitor/PipelinePhaseStrip'
import {
  aggregateStepGroup,
  ANALYST_PHASE_STEPS,
  formatAggregateLine,
  RESEARCH_STEPS,
  RISK_DEBATE_STEPS,
} from '@/features/flow-editor/monitor/phaseAggregates'

const { START_ID, END_ID, MARKET_ID, SIGNAL_ID, RISK_ID, EXEC_ID } = FLOW_NODE_IDS

const TRADER_STEPS: AgentStep[] = ['trader']

type Props = {
  form: NewRunFormState
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>
  streamStatus: RunStatus | 'connecting'
}

function backtestEngineStatus(streamStatus: RunStatus | 'connecting'): 'pending' | 'running' | 'done' {
  if (streamStatus === 'complete') return 'done'
  if (streamStatus === 'error' || streamStatus === 'aborted') return 'pending'
  if (
    streamStatus === 'connecting' ||
    streamStatus === 'running' ||
    streamStatus === 'queued'
  ) {
    return 'running'
  }
  return 'pending'
}

function startMonitorLine(streamStatus: RunStatus | 'connecting'): string {
  if (streamStatus === 'connecting') return 'Connecting to stream…'
  if (streamStatus === 'queued') return 'Queued…'
  if (streamStatus === 'running') return 'Pipeline executing…'
  if (streamStatus === 'complete') return 'Run finished'
  if (streamStatus === 'error') return 'Run ended with error'
  if (streamStatus === 'aborted') return 'Run aborted'
  return ''
}

function endMonitorData(
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>,
  streamStatus: RunStatus | 'connecting',
): {
  monitorOutputStatus: 'pending' | 'running' | 'done'
  monitorOutputLine: string
  monitorOutputLoading: boolean
} {
  if (streamStatus === 'complete') {
    return {
      monitorOutputStatus: 'done',
      monitorOutputLine: 'Output ready',
      monitorOutputLoading: false,
    }
  }
  if (streamStatus === 'error' || streamStatus === 'aborted') {
    return {
      monitorOutputStatus: 'pending',
      monitorOutputLine: 'Stopped',
      monitorOutputLoading: false,
    }
  }
  /** Stream still in flight (connecting / queued / running). */
  const monitorOutputLoading = true
  if (steps.chief_analyst === 'running') {
    return {
      monitorOutputStatus: 'running',
      monitorOutputLine: 'Chief analyst…',
      monitorOutputLoading,
    }
  }
  if (steps.chief_analyst === 'done') {
    return {
      monitorOutputStatus: 'running',
      monitorOutputLine: 'Finalizing…',
      monitorOutputLoading,
    }
  }
  return {
    monitorOutputStatus: 'pending',
    monitorOutputLine: 'Awaiting summary…',
    monitorOutputLoading,
  }
}

function applyStreamToNode(
  node: FlowVisualNode,
  steps: Record<AgentStep, 'pending' | 'running' | 'done'>,
  streamStatus: RunStatus | 'connecting',
): FlowVisualNode {
  if (node.id === START_ID && node.type === 'start' && node.data.kind === 'start') {
    return {
      ...node,
      data: { ...node.data, monitorRunLine: startMonitorLine(streamStatus) },
    }
  }
  if (node.id === END_ID && node.type === 'end' && node.data.kind === 'end') {
    const end = endMonitorData(steps, streamStatus)
    return {
      ...node,
      data: {
        ...node.data,
        monitorOutputStatus: end.monitorOutputStatus,
        monitorOutputLine: end.monitorOutputLine,
        monitorOutputLoading: end.monitorOutputLoading,
      },
    }
  }
  if (node.id === MARKET_ID && node.type === 'pipeline_stage' && node.data.kind === 'pipeline_stage') {
    const st = aggregateStepGroup(steps, ANALYST_PHASE_STEPS)
    const line = formatAggregateLine('Analyst phase', steps, ANALYST_PHASE_STEPS)
    return { ...node, data: { ...node.data, monitorStatus: st, monitorLine: line } }
  }
  if (node.id === SIGNAL_ID && node.type === 'pipeline_stage' && node.data.kind === 'pipeline_stage') {
    const st = aggregateStepGroup(steps, RESEARCH_STEPS)
    const line = formatAggregateLine('Research', steps, RESEARCH_STEPS)
    return { ...node, data: { ...node.data, monitorStatus: st, monitorLine: line } }
  }
  if (node.id === RISK_ID && node.type === 'pipeline_stage' && node.data.kind === 'pipeline_stage') {
    const st = aggregateStepGroup(steps, RISK_DEBATE_STEPS)
    const line = formatAggregateLine('Risk debate', steps, RISK_DEBATE_STEPS)
    return { ...node, data: { ...node.data, monitorStatus: st, monitorLine: line } }
  }
  if (node.id === EXEC_ID && node.type === 'pipeline_stage' && node.data.kind === 'pipeline_stage') {
    const st = aggregateStepGroup(steps, TRADER_STEPS)
    const line = formatAggregateLine('Trader', steps, TRADER_STEPS)
    return { ...node, data: { ...node.data, monitorStatus: st, monitorLine: line } }
  }
  if (node.type === 'agent' && node.data.kind === 'agent') {
    const st = stepStatusForAnalyst(node.data.analystId, steps)
    return { ...node, data: { ...node.data, status: st } }
  }
  if (node.type === 'backtest_engine' && node.data.kind === 'backtest_engine') {
    return {
      ...node,
      data: { ...node.data, status: backtestEngineStatus(streamStatus) },
    }
  }
  if (node.type === 'phase_mini' && node.data.kind === 'phase_mini') {
    const step = node.data.step
    const raw = steps[step]
    const st = raw === 'running' ? 'running' : raw === 'done' ? 'done' : 'pending'
    return { ...node, data: { ...node.data, status: st } }
  }
  return node
}

export default function RunFlowMonitor({ form, steps, streamStatus }: Props) {
  const initial = useMemo(() => formToVisualGraph(form, []), [form])
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowVisualNode>(initial.nodes)

  /** Freeze once the monitor graph includes the swimlane — never recompute on SSE ticks. */
  const [entranceStaggerById, setEntranceStaggerById] = useState<Record<string, number> | null>(null)

  useEffect(() => {
    setNodes((prev) => {
      const prevMain = prev.filter((n) => n.type !== 'phase_mini')
      const phasePos = new Map<string, { x: number; y: number }>()
      for (const n of prev) {
        if (n.type === 'phase_mini') {
          phasePos.set(n.id, { ...n.position })
        }
      }
      const { nodes: base } = formToVisualGraph(form, prevMain)
      const swimlane = buildPhaseSwimlaneNodes(base, phasePos)
      const merged = [...base, ...swimlane]
      return merged.map((node) => applyStreamToNode(node, steps, streamStatus))
    })
  }, [form, steps, streamStatus, setNodes])

  useEffect(() => {
    if (entranceStaggerById !== null) return
    if (!nodes.some((n) => n.type === 'phase_mini')) return
    const m: Record<string, number> = {}
    nodes.forEach((n, i) => {
      m[n.id] = i * 42
    })
    setEntranceStaggerById(m)
  }, [nodes, entranceStaggerById])

  const entranceStaggerMs = useMemo(
    () =>
      entranceStaggerById == null ? undefined : (id: string) => entranceStaggerById[id],
    [entranceStaggerById],
  )

  const edges = useMemo(() => decorateMonitorEdges(buildMonitorEdges(nodes), nodes), [nodes])

  const noopPatch = (_id: string, _patch: Record<string, unknown>) => {}

  const arrangeLayout = useMemo(
    () => (nds: FlowVisualNode[]) => applyDagreLayout(nds, buildMonitorEdges(nds)),
    [],
  )

  return (
    <div className="space-y-0">
      <FlowCanvas
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={() => {}}
        readOnly
        allowNodeDrag
        patchNodeData={noopPatch}
        allowAgentDrop={false}
        setNodes={setNodes}
        tallCanvas
        entranceStaggerMs={entranceStaggerMs}
        arrangeLayout={arrangeLayout}
      />
      <PipelinePhaseStrip steps={steps} />
      <p
        className="text-[10px] mt-2 terminal-text leading-relaxed max-w-[720px]"
        style={{ color: 'var(--text-low)' }}
      >
        Top: analyst palette nodes plus pipeline-stage aggregates (compressed view). Below: full post-analyst LangGraph
        chain (bull → … → chief), one mini-node per streamed step. The phase strip matches the same sequence. For the
        authoritative ordered list, use Overview.
      </p>
    </div>
  )
}
