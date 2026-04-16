'use client'

import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { getMonitorEntranceFadeProps, useFlowRuntime } from '@/features/flow-editor/context/FlowRuntimeContext'

type Data = { kind: 'backtest_engine'; status?: 'pending' | 'running' | 'done' }

type BtNode = Node<Data, 'backtest_engine'>

export default function BacktestEngineNode({ id, data }: NodeProps<BtNode>) {
  const rt = useFlowRuntime()
  const entranceFade = getMonitorEntranceFadeProps(id, rt)
  const status = data.status ?? 'pending'
  const inner = (
    <div
      className={`flow-node rounded-xl min-w-[200px] border px-3 py-3 transition-[border-color,background-color,box-shadow] duration-[180ms] ease-out ${
        status === 'running' ? 'flow-node--backtest-running' : ''
      }`}
      style={{
        background:
          status === 'running'
            ? 'color-mix(in srgb, var(--bg-elevated) 88%, var(--hold) 12%)'
            : 'var(--bg-elevated)',
        borderColor: status === 'running' ? 'color-mix(in srgb, var(--hold-ring) 55%, var(--hold) 45%)' : 'var(--hold-ring)',
        boxShadow:
          status === 'running'
            ? '0 0 28px color-mix(in srgb, var(--hold-bg) 70%, transparent)'
            : '0 0 24px var(--hold-bg)',
      }}
    >
      <Handle type="target" position={Position.Left} className="!bg-[var(--text-low)] !w-2 !h-2" />
      <div className="text-[11px] font-bold" style={{ color: 'var(--hold)' }}>
        Backtest Engine
      </div>
      <p className="text-[10px] mt-1" style={{ color: 'var(--text-mid)' }}>
        Bar loop · execution simulator
      </p>
      <p className="text-[9px] mt-2 terminal-text uppercase tracking-wider" style={{ color: 'var(--text-low)' }}>
        {status === 'pending' && 'Queued'}
        {status === 'running' && 'Running'}
        {status === 'done' && 'Complete'}
      </p>
      <Handle type="source" position={Position.Right} className="!bg-[var(--hold)] !w-2 !h-2" />
    </div>
  )

  if (!entranceFade.enabled) return inner

  return (
    <div className={entranceFade.className} style={entranceFade.style}>
      {inner}
    </div>
  )
}
