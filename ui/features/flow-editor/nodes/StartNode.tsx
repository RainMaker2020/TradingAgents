'use client'

import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { getMonitorEntranceFadeProps, useFlowRuntime } from '@/features/flow-editor/context/FlowRuntimeContext'
import type { StartNodeData } from '@/features/flow-editor/types'

type StartNodeType = Node<StartNodeData, 'start'>
type Props = NodeProps<StartNodeType>

export default function StartNode({ id, data }: Props) {
  const rt = useFlowRuntime()
  const entranceFade = getMonitorEntranceFadeProps(id, rt)
  const ro = rt?.readOnly ?? false

  const patch = (patch: Partial<StartNodeData>) => {
    if (ro) return
    rt?.patchNodeData(id, patch)
  }

  const inner = (
    <div
      className="flow-node flow-node--start rounded-xl min-w-[220px] max-w-[280px] border transition-[border-color,background-color,box-shadow] duration-[180ms] ease-out"
      style={{
        background: 'var(--bg-elevated)',
        borderColor: 'var(--border-raised)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.35)',
      }}
    >
      <Handle type="target" position={Position.Left} className="!bg-[var(--text-low)] !w-2 !h-2" />
      <div
        className="flow-node__head px-3 py-2 rounded-t-xl flex items-center gap-2 border-b"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-card)' }}
      >
        <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-mid)' }}>
          Portfolio Manager
        </span>
      </div>
      {ro && (data.ticker || data.date) ? (
        <div
          className="px-3 py-1.5 border-b text-[9px] terminal-text leading-snug"
          style={{ borderColor: 'var(--border)' }}
        >
          <span style={{ color: 'var(--accent-light)' }}>{data.ticker || '—'}</span>
          <span style={{ color: 'var(--text-low)' }}> · </span>
          <span style={{ color: 'var(--text-mid)' }}>
            {data.mode === 'backtest' && data.end_date ? `${data.date} → ${data.end_date}` : data.date}
          </span>
        </div>
      ) : null}
      {ro && data.monitorRunLine ? (
        <div
          className="px-3 py-1.5 border-b text-[9px] terminal-text leading-snug transition-colors duration-150 ease-out"
          style={{ borderColor: 'var(--border)', color: 'var(--hold)' }}
        >
          {data.monitorRunLine}
        </div>
      ) : null}
      <div className="p-3 space-y-2.5">
        <div>
          <label className="flow-field-label" htmlFor={`${id}-ticker`}>
            Ticker
          </label>
          <input
            id={`${id}-ticker`}
            className="vault-input terminal-text font-bold text-xs w-full"
            style={{ letterSpacing: '0.08em' }}
            value={data.ticker}
            readOnly={ro}
            onChange={(e) => patch({ ticker: e.target.value.toUpperCase() })}
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="flow-field-label" htmlFor={`${id}-date`}>
              Trade date
            </label>
            <input
              id={`${id}-date`}
              type="date"
              className="vault-input terminal-text text-[11px] w-full"
              value={data.date}
              readOnly={ro}
              onChange={(e) => patch({ date: e.target.value })}
            />
          </div>
          {data.mode === 'backtest' && (
            <div>
              <label className="flow-field-label" htmlFor={`${id}-end`}>
                End
              </label>
              <input
                id={`${id}-end`}
                type="date"
                className="vault-input terminal-text text-[11px] w-full"
                value={data.end_date}
                readOnly={ro}
                onChange={(e) => patch({ end_date: e.target.value })}
              />
            </div>
          )}
        </div>
        <div>
          <label className="flow-field-label" htmlFor={`${id}-model`}>
            Model
          </label>
          <input
            id={`${id}-model`}
            className="vault-input terminal-text text-[11px] w-full"
            value={data.deep_think_llm}
            readOnly={ro}
            onChange={(e) => patch({ deep_think_llm: e.target.value })}
          />
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-[var(--accent)] !w-2 !h-2" />
    </div>
  )

  if (!entranceFade.enabled) return inner

  return (
    <div className={entranceFade.className} style={entranceFade.style}>
      {inner}
    </div>
  )
}
