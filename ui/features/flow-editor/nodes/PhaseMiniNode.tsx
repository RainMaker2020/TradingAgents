'use client'

import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { getMonitorEntranceFadeProps, useFlowRuntime } from '@/features/flow-editor/context/FlowRuntimeContext'
import type { PhaseMiniNodeData } from '@/features/flow-editor/types'

type PhaseMini = Node<PhaseMiniNodeData, 'phase_mini'>
type Props = NodeProps<PhaseMini>

export default function PhaseMiniNode({ id, data }: Props) {
  const rt = useFlowRuntime()
  const entranceFade = getMonitorEntranceFadeProps(id, rt)
  const status = data.status ?? 'pending'
  const border =
    status === 'running'
      ? 'linear-gradient(145deg, rgba(167,139,250,0.42) 0%, rgba(0,196,232,0.28) 100%)'
      : status === 'done'
        ? 'linear-gradient(145deg, rgba(0,224,120,0.28) 0%, rgba(0,196,232,0.2) 100%)'
        : 'linear-gradient(145deg, rgba(120,120,160,0.18) 0%, rgba(80,80,120,0.12) 100%)'

  const inner = (
    <div
      className={`flow-node flow-node--phase-mini rounded-lg min-w-[96px] max-w-[108px] p-0.5 transition-[background,border-color,box-shadow] duration-[180ms] ease-out ${
        status === 'running' ? 'flow-node--phase-mini-running' : ''
      }`}
      style={{ background: border }}
    >
      <div
        className="rounded-[6px] px-2 py-1.5 h-full"
        style={{ background: 'var(--bg-elevated)' }}
      >
        <Handle type="target" position={Position.Left} className="!bg-[var(--text-low)] !w-1.5 !h-1.5" />
        <div
          className="text-[9px] font-bold leading-tight"
          style={{ color: 'var(--text-high)' }}
          title={data.label}
        >
          {data.label}
        </div>
        <div
          className="mt-1 text-[8px] px-1.5 py-0.5 rounded terminal-text uppercase tracking-wider transition-colors duration-150 ease-out"
          style={{
            background: 'var(--bg-card)',
            color:
              status === 'running' ? 'var(--hold)' : status === 'done' ? 'var(--accent-light)' : 'var(--text-mid)',
            border: '1px solid var(--border)',
          }}
        >
          {status === 'pending' && 'Queued'}
          {status === 'running' && 'Active'}
          {status === 'done' && 'Done'}
        </div>
        <Handle type="source" position={Position.Right} className="!bg-[var(--accent)] !w-1.5 !h-1.5" />
      </div>
    </div>
  )

  if (!entranceFade.enabled) return inner

  return (
    <div className={entranceFade.className} style={entranceFade.style}>
      {inner}
    </div>
  )
}
