'use client'

import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { getMonitorEntranceFadeProps, useFlowRuntime } from '@/features/flow-editor/context/FlowRuntimeContext'
import type { AgentNodeData } from '@/features/flow-editor/types'

type AgentVisualData = AgentNodeData & { status?: 'pending' | 'running' | 'done' }

type AgentNodeType = Node<AgentVisualData, 'agent'>
type Props = NodeProps<AgentNodeType>

export default function AgentNode({ id, data }: Props) {
  const rt = useFlowRuntime()
  const entranceFade = getMonitorEntranceFadeProps(id, rt)
  const status = data.status ?? 'pending'
  const border =
    status === 'running'
      ? 'linear-gradient(145deg, rgba(167,139,250,0.5) 0%, rgba(0,196,232,0.35) 100%)'
      : status === 'done'
        ? 'linear-gradient(145deg, rgba(0,224,120,0.35) 0%, rgba(0,196,232,0.25) 100%)'
        : 'linear-gradient(145deg, rgba(120,120,160,0.2) 0%, rgba(80,80,120,0.15) 100%)'

  const inner = (
    <div
      className={`flow-node flow-node--agent rounded-xl min-w-[180px] max-w-[220px] p-0.5 transition-[background,border-color,box-shadow] duration-[180ms] ease-out ${
        status === 'running' ? 'flow-node--agent-running' : ''
      }`}
      style={{ background: border }}
    >
      <div
        className="rounded-[10px] px-3 py-2.5 h-full"
        style={{ background: 'var(--bg-elevated)' }}
      >
        <Handle type="target" position={Position.Left} className="!bg-[var(--text-low)] !w-2 !h-2" />
        <div className="text-[11px] font-bold" style={{ color: 'var(--text-high)' }}>
          {data.label}
        </div>
        <div className="text-[9px] mt-1 terminal-text uppercase tracking-wider" style={{ color: 'var(--text-low)' }}>
          Strategy analyst
        </div>
        <div
          className="mt-2 text-[10px] px-2 py-1 rounded-md terminal-text transition-colors duration-150 ease-out"
          style={{
            background: 'var(--bg-card)',
            color:
              status === 'running' ? 'var(--hold)' : status === 'done' ? 'var(--accent-light)' : 'var(--text-mid)',
            border: '1px solid var(--border)',
          }}
        >
          {status === 'pending' && 'Queued'}
          {status === 'running' && 'In progress'}
          {status === 'done' && 'Complete'}
        </div>
        <Handle type="source" position={Position.Right} className="!bg-[var(--accent)] !w-2 !h-2" />
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
