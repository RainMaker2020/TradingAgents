'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type NodeChange,
  type OnEdgesChange,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { FlowVisualNode } from '@/features/flow-editor/types'
import { FlowRuntimeProvider } from '@/features/flow-editor/context/FlowRuntimeContext'
import { analystLabel } from '@/features/flow-editor/analystCatalog'
import StartNode from '@/features/flow-editor/nodes/StartNode'
import AgentNode from '@/features/flow-editor/nodes/AgentNode'
import EndNode from '@/features/flow-editor/nodes/EndNode'
import BacktestEngineNode from '@/features/flow-editor/nodes/BacktestEngineNode'
import PipelineStageNode from '@/features/flow-editor/nodes/PipelineStageNode'
import PhaseMiniNode from '@/features/flow-editor/nodes/PhaseMiniNode'
import '@/features/flow-editor/styles/flow-editor.css'

type FlowCanvasInnerProps = {
  nodes: FlowVisualNode[]
  edges: Edge[]
  onNodesChange: (changes: NodeChange<FlowVisualNode>[]) => void
  onEdgesChange: OnEdgesChange
  readOnly: boolean
  /** When true with readOnly, inputs stay locked but nodes can be dragged (run monitor). */
  allowNodeDrag?: boolean
  patchNodeData: (nodeId: string, patch: Record<string, unknown>) => void
  allowAgentDrop: boolean
  setNodes: React.Dispatch<React.SetStateAction<FlowVisualNode[]>>
  /** Taller viewport for run monitor (second swimlane). */
  tallCanvas?: boolean
  /** Run monitor: staggered fade-in delays per node id (frozen after first full graph). */
  entranceStaggerMs?: (nodeId: string) => number | undefined
  /** Dagre (or custom) relayout; when set, an Arrange control is shown. */
  arrangeLayout?: (nodes: FlowVisualNode[]) => FlowVisualNode[]
}

function FlowCanvasInner({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  readOnly,
  allowNodeDrag = false,
  patchNodeData,
  allowAgentDrop,
  setNodes,
  tallCanvas,
  entranceStaggerMs,
  arrangeLayout,
}: FlowCanvasInnerProps) {
  const { screenToFlowPosition, fitView } = useReactFlow()
  const [monitorEntranceLayoutReady, setMonitorEntranceLayoutReady] = useState(false)
  const didFitForMonitorEntrance = useRef(false)

  /** After the monitor graph is fully laid out (stagger map present), fit once then allow entrance fade. */
  useEffect(() => {
    if (!entranceStaggerMs) {
      didFitForMonitorEntrance.current = false
      setMonitorEntranceLayoutReady(false)
      return
    }
    if (didFitForMonitorEntrance.current) return
    didFitForMonitorEntrance.current = true
    void fitView({ padding: 0.18, duration: 0 }).then(() => {
      requestAnimationFrame(() => setMonitorEntranceLayoutReady(true))
    })
  }, [entranceStaggerMs, fitView])

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  const nodeInteraction = allowNodeDrag || !readOnly

  const handleArrange = useCallback(() => {
    if (!arrangeLayout) return
    setNodes((nds) => arrangeLayout(nds))
    requestAnimationFrame(() => {
      void fitView({ padding: 0.18, duration: 280 })
    })
  }, [arrangeLayout, setNodes, fitView])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      if (!allowAgentDrop || readOnly) return
      const raw = e.dataTransfer.getData('application/reactflow')
      if (!raw) return
      let parsed: { type?: string; analystId?: string }
      try {
        parsed = JSON.parse(raw) as { type?: string; analystId?: string }
      } catch {
        return
      }
      const analystId = parsed.analystId
      if (parsed.type !== 'agent' || !analystId) return
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY })
      const id = `node-agent-${analystId}`
      setNodes((nds) => {
        if (nds.some((n) => n.id === id)) return nds
        const next: FlowVisualNode = {
          id,
          type: 'agent',
          position,
          data: {
            kind: 'agent',
            analystId,
            label: analystLabel(analystId),
          },
        }
        return nds.concat(next)
      })
    },
    [allowAgentDrop, readOnly, screenToFlowPosition, setNodes],
  )

  const nodeTypes = useMemo(
    () => ({
      start: StartNode,
      agent: AgentNode,
      end: EndNode,
      backtest_engine: BacktestEngineNode,
      pipeline_stage: PipelineStageNode,
      phase_mini: PhaseMiniNode,
    }),
    [],
  )

  const runtime = useMemo(
    () => ({
      readOnly,
      patchNodeData,
      entranceStaggerMs,
      entranceLayoutReady: entranceStaggerMs ? monitorEntranceLayoutReady : true,
    }),
    [readOnly, patchNodeData, entranceStaggerMs, monitorEntranceLayoutReady],
  )

  return (
    <FlowRuntimeProvider value={runtime}>
      <div
        className="flow-canvas-wrap flow-canvas-wrap--dataflow relative w-full rounded-xl overflow-hidden border"
        style={{
          borderColor: 'var(--border-raised)',
          height: tallCanvas ? 'min(78vh, 920px)' : 'min(72vh, 780px)',
          minHeight: tallCanvas ? 'min(78vh, 920px)' : 'min(72vh, 780px)',
          background: 'var(--bg-surface)',
        }}
      >
        {arrangeLayout ? (
          <div className="absolute top-2 right-2 z-10 flex items-center gap-2">
            <button
              type="button"
              className="btn-secondary !h-[30px] !px-3 !py-0 text-[11px] font-semibold"
              onClick={handleArrange}
            >
              Arrange
            </button>
          </div>
        ) : null}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={nodeInteraction ? onNodesChange : () => {}}
          onEdgesChange={readOnly ? () => {} : onEdgesChange}
          nodesDraggable={nodeInteraction}
          nodesConnectable={false}
          elementsSelectable={nodeInteraction}
          panOnScroll
          zoomOnScroll
          minZoom={0.28}
          maxZoom={1.5}
          fitView
          fitViewOptions={{ padding: 0.18 }}
          nodeTypes={nodeTypes}
          onDrop={onDrop}
          onDragOver={onDragOver}
          proOptions={{ hideAttribution: true }}
          defaultEdgeOptions={{
            type: 'smoothstep',
            style: {
              stroke: 'var(--flow-edge)',
              strokeWidth: 2,
              strokeLinecap: 'round',
              strokeLinejoin: 'round',
            },
          }}
        >
          <Background variant={BackgroundVariant.Dots} gap={22} size={1.25} color="rgba(95, 105, 160, 0.11)" />
          <Controls
            className="!bg-[var(--bg-elevated)] !border !shadow-none"
            style={{ borderColor: 'var(--border-raised)' }}
          />
          <MiniMap
            pannable
            zoomable
            maskColor="rgba(5,5,8,0.82)"
            className="!bg-[var(--bg-card)]"
            nodeStrokeColor="var(--accent)"
            nodeColor="var(--bg-elevated)"
          />
        </ReactFlow>
      </div>
    </FlowRuntimeProvider>
  )
}

export default function FlowCanvas(props: FlowCanvasInnerProps) {
  return (
    <ReactFlowProvider>
      <FlowCanvasInner {...props} />
    </ReactFlowProvider>
  )
}
