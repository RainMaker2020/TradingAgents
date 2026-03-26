import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import RunConfigForm from '@/features/new-run/components/RunConfigForm'
import { getProviderModels } from '@/lib/api-client'

const mockPush = jest.fn()
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: mockPush }) }))
jest.mock('@/lib/api-client', () => ({
  createRun: jest.fn().mockResolvedValue({ id: 'test123' }),
  getProviderModels: jest.fn().mockResolvedValue({ provider: 'openai', models: ['gpt-5-mini'], error: null }),
}))

test('renders ticker and date inputs', () => {
  render(<RunConfigForm />)
  expect(screen.getByPlaceholderText('e.g. NVDA')).toBeInTheDocument()
  expect(screen.getByLabelText(/trade date/i)).toBeInTheDocument()
})

test('submitting navigates to run detail page', async () => {
  render(<RunConfigForm />)
  fireEvent.change(screen.getByPlaceholderText('e.g. NVDA'), {
    target: { value: 'NVDA' },
  })
  fireEvent.change(screen.getByLabelText(/trade date/i), {
    target: { value: '2024-05-10' },
  })
  fireEvent.click(screen.getByText(/run analysis/i))
  await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/runs/test123'))
})

test('switches to deepseek defaults', async () => {
  render(<RunConfigForm />)

  fireEvent.click(screen.getByRole('tab', { name: 'DeepSeek' }))

  // After event settles, all three fields must be consistent with DeepSeek defaults.
  // No stale OpenAI model name should remain selected.
  await waitFor(() => {
    expect(screen.getByDisplayValue('deepseek-reasoner')).toBeInTheDocument()
  })
  expect(screen.getByRole('tab', { name: 'DeepSeek' })).toHaveAttribute('aria-selected', 'true')
  expect(screen.getByDisplayValue('deepseek-chat')).toBeInTheDocument()
  expect(screen.queryByDisplayValue('gpt-5.2')).not.toBeInTheDocument()
})

test('shows DeepSeek defaults when model fetch fails', async () => {
  jest.mocked(getProviderModels)
    .mockResolvedValueOnce({ provider: 'openai', models: ['gpt-5-mini'], error: null })
    .mockRejectedValueOnce(new Error('No API key'))

  render(<RunConfigForm />)

  fireEvent.click(screen.getByRole('tab', { name: 'DeepSeek' }))

  // After the failed fetch settles, defaults remain and warning is shown.
  await waitFor(() => {
    expect(screen.getByText(/model list:/i)).toBeInTheDocument()
  })
  expect(screen.getByRole('tab', { name: 'DeepSeek' })).toHaveAttribute('aria-selected', 'true')
  expect(screen.getByDisplayValue('deepseek-reasoner')).toBeInTheDocument()
  expect(screen.getByDisplayValue('deepseek-chat')).toBeInTheDocument()
})
