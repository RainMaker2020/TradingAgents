import { validateRunTarget } from '@/features/new-run/validation'
import type { NewRunFormState } from '@/features/new-run/types'
import { DEFAULT_FORM } from '@/features/new-run/types'

function baseForm(over: Partial<NewRunFormState>): NewRunFormState {
  return { ...DEFAULT_FORM, ...over }
}

test('validateRunTarget accepts BTC-USD', () => {
  const e = validateRunTarget(
    baseForm({ ticker: 'BTC-USD', date: '2024-01-02', mode: 'graph' }),
  )
  expect(e.ticker).toBeUndefined()
})

test('validateRunTarget accepts GC=F and ^GSPC', () => {
  expect(
    validateRunTarget(baseForm({ ticker: 'GC=F', date: '2024-01-02', mode: 'graph' })).ticker,
  ).toBeUndefined()
  expect(
    validateRunTarget(baseForm({ ticker: '^GSPC', date: '2024-01-02', mode: 'graph' })).ticker,
  ).toBeUndefined()
})

test('validateRunTarget rejects empty and junk tickers', () => {
  expect(validateRunTarget(baseForm({ ticker: '', date: '2024-01-02', mode: 'graph' })).ticker).toBe(
    'Ticker symbol is required.',
  )
  expect(
    validateRunTarget(baseForm({ ticker: 'FOO/BAR', date: '2024-01-02', mode: 'graph' })).ticker,
  ).toBeDefined()
})
