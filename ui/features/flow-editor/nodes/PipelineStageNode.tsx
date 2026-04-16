'use client'

import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { getMonitorEntranceFadeProps, useFlowRuntime } from '@/features/flow-editor/context/FlowRuntimeContext'
import type { PipelineStageId, PipelineStageNodeData } from '@/features/flow-editor/types'

type PipelineNode = Node<PipelineStageNodeData, 'pipeline_stage'>

const STAGE_META: Record<
  PipelineStageId,
  { title: string; subtitle: string; borderVar: string; accentVar: string }
> = {
  market_data: {
    title: 'Market data ingestion',
    subtitle: 'Live price feeds · order book depth',
    borderVar: 'var(--border-active)',
    accentVar: 'var(--accent)',
  },
  signal_strategy: {
    title: 'Signal & strategy',
    subtitle: 'Multi-agent analysis · thesis synthesis',
    borderVar: 'var(--gold-ring)',
    accentVar: 'var(--gold)',
  },
  risk: {
    title: 'Risk management',
    subtitle: 'Exposure limits · pre-trade checks',
    borderVar: 'var(--hold-ring)',
    accentVar: 'var(--hold)',
  },
  execution: {
    title: 'Execution engine',
    subtitle: 'Smart routing · broker connectivity',
    borderVar: 'var(--buy-ring)',
    accentVar: 'var(--buy)',
  },
}

type Props = NodeProps<PipelineNode>

function monitorChipLabel(st: 'pending' | 'running' | 'done'): string {
  if (st === 'running') return 'In progress'
  if (st === 'done') return 'Complete'
  return 'Queued'
}

export default function PipelineStageNode({ id, data }: Props) {
  const rt = useFlowRuntime()
  const entranceFade = getMonitorEntranceFadeProps(id, rt)
  const meta = STAGE_META[data.stage]
  const hasMonitor = data.monitorStatus != null
  const st = data.monitorStatus
  const running = st === 'running'

  const inner = (
    <div
      className={`flow-node flow-node--pipeline rounded-xl min-w-[200px] max-w-[220px] border px-3 py-2.5 transition-[border-color,background-color,box-shadow] duration-[180ms] ease-out ${
        running ? 'flow-node--pipeline-running' : ''
      }`}
      style={{
        background: 'var(--bg-elevated)',
        borderColor: meta.borderVar,
        boxShadow: running
          ? '0 14px 40px rgba(0,0,0,0.45), 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent)'
          : '0 14px 40px rgba(0,0,0,0.45)',
      }}
    >
      <Handle type="target" position={Position.Left} className="!w-2 !h-2" style={{ background: meta.accentVar }} />
      <div className="text-[10px] font-bold uppercase tracking-widest" style={{ color: meta.accentVar }}>
        Pipeline
      </div>
      <div className="text-[12px] font-bold mt-1 leading-snug" style={{ color: 'var(--text-high)' }}>
        {meta.title}
      </div>
      <p className="text-[9px] mt-1 leading-relaxed" style={{ color: 'var(--text-mid)' }}>
        {hasMonitor && data.monitorLine ? data.monitorLine : meta.subtitle}
      </p>
      {hasMonitor && st != null && (
        <div
          className="mt-2 text-[10px] px-2 py-1 rounded-md terminal-text transition-colors duration-150 ease-out"
          style={{
            background: 'var(--bg-card)',
            color: st === 'running' ? 'var(--hold)' : st === 'done' ? 'var(--accent-light)' : 'var(--text-mid)',
            border: '1px solid var(--border)',
          }}
        >
          {monitorChipLabel(st)}
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!w-2 !h-2" style={{ background: meta.accentVar }} />
    </div>
  )

  if (!entranceFade.enabled) return inner

  return (
    <div className={entranceFade.className} style={entranceFade.style}>
      {inner}
    </div>
  )
}
