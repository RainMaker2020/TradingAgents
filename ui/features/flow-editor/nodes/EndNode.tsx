'use client'

import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { getMonitorEntranceFadeProps, useFlowRuntime } from '@/features/flow-editor/context/FlowRuntimeContext'
import type { EndNodeData } from '@/features/flow-editor/types'

type EndNodeType = Node<EndNodeData, 'end'>
type Props = NodeProps<EndNodeType>

export default function EndNode({ id, data }: Props) {
  const rt = useFlowRuntime()
  const entranceFade = getMonitorEntranceFadeProps(id, rt)
  const ro = rt?.readOnly ?? false

  const patch = (patch: Partial<EndNodeData>) => {
    if (ro) return
    rt?.patchNodeData(id, patch)
  }

  const parseNum = (v: string): number => (v.trim() === '' ? Number.NaN : Number(v))

  const inner = (
    <div
      className="flow-node flow-node--end rounded-xl min-w-[220px] max-w-[260px] border transition-[border-color,background-color,box-shadow] duration-[180ms] ease-out"
      style={{
        background: 'var(--bg-elevated)',
        borderColor: 'var(--border-raised)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.35)',
      }}
    >
      <Handle type="target" position={Position.Left} className="!bg-[var(--text-low)] !w-2 !h-2" />
      <div
        className="flow-node__head px-3 py-2 rounded-t-xl border-b flex items-center gap-2"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-card)' }}
      >
        <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-mid)' }}>
          Simulation Output
        </span>
      </div>
      {ro && (data.monitorOutputLine != null || data.monitorOutputLoading) ? (
        <div
          className="px-3 py-1.5 border-b flex items-center gap-2 text-[9px] terminal-text leading-snug transition-colors duration-150 ease-out"
          style={{
            borderColor: 'var(--border)',
            color:
              data.monitorOutputStatus === 'running'
                ? 'var(--hold)'
                : data.monitorOutputStatus === 'done'
                  ? 'var(--accent-light)'
                  : 'var(--text-mid)',
          }}
        >
          {data.monitorOutputLoading ? (
            <span
              className="inline-block w-3.5 h-3.5 shrink-0 rounded-full border-2 animate-spin"
              style={{ borderColor: 'var(--accent)', borderTopColor: 'transparent' }}
              aria-hidden
            />
          ) : null}
          {data.monitorOutputLine ? <span className="min-w-0">{data.monitorOutputLine}</span> : null}
        </div>
      ) : null}
      <div className="p-3 grid grid-cols-2 gap-2">
        <div>
          <label className="flow-field-label" htmlFor={`${id}-cash`}>
            Initial cash
          </label>
          <input
            id={`${id}-cash`}
            type="number"
            className="vault-input terminal-text text-[11px] w-full"
            value={Number.isFinite(data.initial_cash) ? data.initial_cash : ''}
            readOnly={ro}
            onChange={(e) => patch({ initial_cash: parseNum(e.target.value) })}
          />
        </div>
        <div>
          <label className="flow-field-label" htmlFor={`${id}-slip`}>
            Slippage bps
          </label>
          <input
            id={`${id}-slip`}
            type="number"
            className="vault-input terminal-text text-[11px] w-full"
            value={Number.isFinite(data.slippage_bps) ? data.slippage_bps : ''}
            readOnly={ro}
            onChange={(e) => patch({ slippage_bps: parseNum(e.target.value) })}
          />
        </div>
        <div>
          <label className="flow-field-label" htmlFor={`${id}-fee`}>
            Fee / trade
          </label>
          <input
            id={`${id}-fee`}
            type="number"
            className="vault-input terminal-text text-[11px] w-full"
            value={Number.isFinite(data.fee_per_trade) ? data.fee_per_trade : ''}
            readOnly={ro}
            onChange={(e) => patch({ fee_per_trade: parseNum(e.target.value) })}
          />
        </div>
        <div>
          <label className="flow-field-label" htmlFor={`${id}-max`}>
            Max pos %
          </label>
          <input
            id={`${id}-max`}
            type="number"
            className="vault-input terminal-text text-[11px] w-full"
            value={Number.isFinite(data.max_position_pct) ? data.max_position_pct : ''}
            readOnly={ro}
            onChange={(e) => patch({ max_position_pct: parseNum(e.target.value) })}
          />
        </div>
      </div>
      <div className="px-3 pb-3 text-[9px] terminal-text" style={{ color: 'var(--text-low)' }}>
        Maps to simulation_config on launch
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
