'use client'

import { useCallback, useMemo, useState } from 'react'
import type { NewRunFormState } from '@/features/new-run/types'
import { useRunFlowCanvas } from '@/features/flow-editor/hooks/useRunFlowCanvas'
import FlowCanvas from '@/features/flow-editor/components/FlowCanvas'
import { applyDagreLayout } from '@/features/flow-editor/layout/applyDagreLayout'
import { edgesFromNodes } from '@/features/flow-editor/sync/formSnapshot'
import type { FlowVisualNode } from '@/features/flow-editor/types'
import FlowHeader from '@/features/flow-editor/components/FlowHeader'
import FlowsSidebar from '@/features/flow-editor/components/FlowsSidebar'
import ComponentsPalette from '@/features/flow-editor/components/ComponentsPalette'
import { buildFlowDocument, upsertFlowDocument } from '@/features/flow-editor/storage/flowStorage'
import type { FlowDocument } from '@/features/flow-editor/types'

type Tab = 'flow' | 'settings'

type Props = {
  form: NewRunFormState
  onFormChange: (next: NewRunFormState) => void
  onExecutionModeChange?: (mode: 'graph' | 'backtest') => void
  /** Full form UI (All settings tab). */
  settingsPanel: React.ReactNode
}

export default function RunFlowWorkspace({
  form,
  onFormChange,
  onExecutionModeChange,
  settingsPanel,
}: Props) {
  const [tab, setTab] = useState<Tab>('flow')
  const [flowListKey, setFlowListKey] = useState(0)
  const [activeFlowId, setActiveFlowId] = useState<string | null>(null)

  const {
    nodes,
    edges,
    setNodes,
    onNodesChange,
    onEdgesChange,
    patchNodeData,
  } = useRunFlowCanvas(form, onFormChange)

  const handleLoad = useCallback(
    (doc: FlowDocument) => {
      if (doc.form) {
        onFormChange(doc.form)
        onExecutionModeChange?.(doc.form.mode)
        setActiveFlowId(doc.id)
      }
    },
    [onFormChange, onExecutionModeChange],
  )

  const handleSave = useCallback(
    (name: string) => {
      const doc = buildFlowDocument(name, form)
      upsertFlowDocument(doc)
      setFlowListKey((k) => k + 1)
      setActiveFlowId(doc.id)
    },
    [form],
  )

  const flowTabs = useMemo(() => {
    if (!activeFlowId) return undefined
    return [{ id: activeFlowId, label: 'Active snapshot', active: true }]
  }, [activeFlowId])

  const arrangeLayout = useCallback(
    (nds: FlowVisualNode[]) => applyDagreLayout(nds, edgesFromNodes(nds)),
    [],
  )

  return (
    <div className="space-y-0 rounded-xl border overflow-hidden" style={{ borderColor: 'var(--border-raised)' }}>
      <FlowHeader active={tab} onChange={setTab} flowTabs={flowTabs} />
      {/* Keep settings mounted while on Flow tab so RunConfigForm effects (settings hydrate, autosave) still run. */}
      <div className={tab === 'flow' ? 'block' : 'hidden'} aria-hidden={tab !== 'flow'}>
        <div className="flex flex-col lg:flex-row gap-2 p-2" style={{ background: 'var(--bg-surface)' }}>
          <FlowsSidebar key={flowListKey} onLoad={handleLoad} onSave={handleSave} />
          <div className="flex-1 min-w-0">
            <FlowCanvas
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              readOnly={false}
              patchNodeData={patchNodeData}
              allowAgentDrop={form.mode === 'graph'}
              setNodes={setNodes}
              arrangeLayout={arrangeLayout}
            />
          </div>
          <ComponentsPalette disabled={form.mode !== 'graph'} />
        </div>
      </div>
      <div className={tab === 'settings' ? 'block' : 'hidden'} aria-hidden={tab !== 'settings'}>
        <div className="p-3" style={{ background: 'var(--bg-surface)' }}>
          {settingsPanel}
        </div>
      </div>
    </div>
  )
}
