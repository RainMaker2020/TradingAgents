import { DEFAULT_FORM } from '@/features/new-run/types'
import { edgesFromNodes, formToVisualGraph, visualGraphToForm } from '@/features/flow-editor/sync/formSnapshot'

test('graph mode: form round-trips through visual graph for key fields', () => {
  const form = {
    ...DEFAULT_FORM,
    ticker: 'AAPL',
    date: '2024-06-01',
    mode: 'graph' as const,
    enabled_analysts: ['market', 'news'],
    deep_think_llm: 'gpt-test',
    llm_provider: 'openai',
  }
  const { nodes, edges } = formToVisualGraph(form, [])
  expect(edges.length).toBeGreaterThan(0)
  const back = visualGraphToForm(form, nodes)
  expect(back.ticker).toBe('AAPL')
  expect(back.date).toBe('2024-06-01')
  expect(back.mode).toBe('graph')
  expect(back.enabled_analysts.sort()).toEqual(['market', 'news'].sort())
  expect(back.deep_think_llm).toBe('gpt-test')
})

test('edgesFromNodes chains pipeline when no agents', () => {
  const { nodes } = formToVisualGraph({ ...DEFAULT_FORM, mode: 'graph', enabled_analysts: [] }, [])
  const e = edgesFromNodes(nodes)
  expect(e.some((x) => x.source === 'node-start' && x.target === 'node-pipeline-market')).toBe(true)
  expect(e.some((x) => x.source === 'node-pipeline-execution' && x.target === 'node-end')).toBe(true)
})

test('backtest mode: no analyst list mutation from graph', () => {
  const form = {
    ...DEFAULT_FORM,
    mode: 'backtest' as const,
    enabled_analysts: ['market'],
  }
  const { nodes } = formToVisualGraph(form, [])
  const next = visualGraphToForm(form, nodes)
  expect(next.enabled_analysts).toEqual(['market'])
})

test('backtest mode: pipeline includes market, signal, backtest, risk, execution', () => {
  const { nodes, edges } = formToVisualGraph({ ...DEFAULT_FORM, mode: 'backtest' }, [])
  expect(nodes.some((n) => n.id === 'node-backtest-engine')).toBe(true)
  expect(edges.some((e) => e.source === 'node-pipeline-signal' && e.target === 'node-backtest-engine')).toBe(true)
  expect(edges.some((e) => e.source === 'node-backtest-engine' && e.target === 'node-pipeline-risk')).toBe(true)
})
