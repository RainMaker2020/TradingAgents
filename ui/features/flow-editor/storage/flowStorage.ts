import type { NewRunFormState } from '@/features/new-run/types'
import type { FlowDocument } from '@/features/flow-editor/types'

const KEY = 'tradingagents.flow-documents.v1'

export type StoredFlowList = {
  flows: FlowDocument[]
}

export function loadFlowDocuments(): FlowDocument[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as StoredFlowList
    return Array.isArray(parsed.flows) ? parsed.flows : []
  } catch {
    return []
  }
}

export function persistFlowDocuments(flows: FlowDocument[]): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(KEY, JSON.stringify({ flows }))
  } catch {
    /* ignore quota */
  }
}

export function upsertFlowDocument(doc: FlowDocument): void {
  const flows = loadFlowDocuments().filter((f) => f.id !== doc.id)
  flows.unshift(doc)
  persistFlowDocuments(flows.slice(0, 40))
}

/** Save a named snapshot of the run configuration (visual layout is rebuilt from form). */
export function buildFlowDocument(name: string, form: NewRunFormState): FlowDocument {
  const id = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `flow-${Date.now()}`
  return {
    id,
    name: name.trim() || 'Untitled flow',
    updatedAt: new Date().toISOString(),
    nodes: [],
    edges: [],
    form,
  }
}
