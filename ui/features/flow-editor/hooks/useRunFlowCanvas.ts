'use client'

import { useCallback, useEffect, useRef } from 'react'
import { useEdgesState, useNodesState, type NodeChange } from '@xyflow/react'
import type { NewRunFormState } from '@/features/new-run/types'
import type { FlowVisualNode } from '@/features/flow-editor/types'
import { edgesFromNodes, formToVisualGraph, visualGraphToForm } from '@/features/flow-editor/sync/formSnapshot'

function nodeDataSignature(nodes: FlowVisualNode[]): string {
  const sorted = [...nodes].sort((a, b) => a.id.localeCompare(b.id))
  return JSON.stringify(
    sorted.map((n) => ({
      id: n.id,
      type: n.type,
      data: n.data,
    })),
  )
}

function shallowFormEquals(a: NewRunFormState, b: NewRunFormState): boolean {
  const keys = Object.keys(a) as (keyof NewRunFormState)[]
  return keys.every((k) => a[k] === b[k])
}

export function useRunFlowCanvas(
  form: NewRunFormState,
  onFormChange: (next: NewRunFormState) => void,
) {
  const initial = formToVisualGraph(form, [])
  const [nodes, setNodes, onNodesChangeBase] = useNodesState<FlowVisualNode>(initial.nodes)
  const [edges, setEdges, onEdgesChangeBase] = useEdgesState(edgesFromNodes(initial.nodes))

  const formRef = useRef(form)
  formRef.current = form

  const nodesRef = useRef(nodes)
  nodesRef.current = nodes

  const syncingFromFormRef = useRef(false)
  const syncingFromGraphRef = useRef(false)
  const skipNextFormToGraphSyncRef = useRef(false)
  const lastDataSigRef = useRef(nodeDataSignature(initial.nodes))

  /** Form changed (e.g. RunConfigForm): rebuild graph while keeping stable positions. */
  useEffect(() => {
    if (syncingFromGraphRef.current) return
    if (skipNextFormToGraphSyncRef.current) {
      skipNextFormToGraphSyncRef.current = false
      return
    }
    syncingFromFormRef.current = true
    const { nodes: nextNodes } = formToVisualGraph(form, nodesRef.current)
    setNodes(nextNodes)
    lastDataSigRef.current = nodeDataSignature(nextNodes)
    queueMicrotask(() => {
      syncingFromFormRef.current = false
    })
  }, [form, setNodes, setEdges])

  /** Canvas structure/data changed: push snapshot into run configuration. */
  useEffect(() => {
    if (syncingFromFormRef.current) return
    const sig = nodeDataSignature(nodes)
    if (sig === lastDataSigRef.current) return
    lastDataSigRef.current = sig
    const next = visualGraphToForm(formRef.current, nodes)
    if (shallowFormEquals(next, formRef.current)) return
    skipNextFormToGraphSyncRef.current = true
    syncingFromGraphRef.current = true
    onFormChange(next)
    queueMicrotask(() => {
      syncingFromGraphRef.current = false
    })
  }, [nodes, onFormChange])

  /** Keep wiring consistent when nodes are added (palette drop) before form sync completes. */
  useEffect(() => {
    setEdges(edgesFromNodes(nodes))
  }, [nodes, setEdges])

  const onNodesChange = useCallback(
    (changes: NodeChange<FlowVisualNode>[]) => {
      onNodesChangeBase(changes)
    },
    [onNodesChangeBase],
  )

  const onEdgesChange = useCallback(
    (changes: Parameters<typeof onEdgesChangeBase>[0]) => {
      /** Edges are derived from configuration; ignore user edge edits. */
      onEdgesChangeBase(changes)
    },
    [onEdgesChangeBase],
  )

  /** Update a single node's `data` from custom node UI (controlled writes). */
  const patchNodeData = useCallback(
    (nodeId: string, patch: Partial<FlowVisualNode['data']>) => {
      setNodes((prev) =>
        prev.map((n) => {
          if (n.id !== nodeId) return n
          return { ...n, data: { ...n.data, ...patch } as FlowVisualNode['data'] }
        }),
      )
    },
    [setNodes],
  )

  return {
    nodes,
    edges,
    setNodes,
    setEdges,
    onNodesChange,
    onEdgesChange,
    patchNodeData,
  }
}
