import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import RunConfigForm from '@/features/new-run/components/RunConfigForm'
import { ApiError, createRun, getProviderModels } from '@/lib/api-client'

const mockPush = jest.fn()
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: mockPush }) }))
jest.mock('@/lib/api-client', () => {
  const actual = jest.requireActual('@/lib/api-client')
  return {
    ...actual,
    createRun: jest.fn().mockResolvedValue({ id: 'test123' }),
    getProviderModels: jest.fn().mockResolvedValue({
      provider: 'openai',
      models: ['gpt-5-mini'],
      error: null,
    }),
  }
})

beforeEach(() => {
  jest.clearAllMocks()
  jest.mocked(createRun).mockResolvedValue({ id: 'test123' })
  jest.mocked(getProviderModels).mockResolvedValue({
    provider: 'openai',
    models: ['gpt-5-mini'],
    error: null,
  })
})

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
  expect(createRun).toHaveBeenCalledWith(
    expect.objectContaining({
      simulation_config: {
        initial_cash: 100000,
        slippage_bps: 5,
        fee_per_trade: 1,
        max_position_pct: 10,
      },
    }),
  )
})

test('default simulation fields render with expected values', () => {
  render(<RunConfigForm />)
  expect(screen.getByLabelText(/initial cash/i)).toHaveValue(100000)
  expect(screen.getByLabelText(/slippage \(bps\)/i)).toHaveValue(5)
  expect(screen.getByLabelText(/fee per trade/i)).toHaveValue(1)
  expect(screen.getByLabelText(/max position size/i)).toHaveValue(10)
})

test('edited simulation values are submitted as friendly units', async () => {
  render(<RunConfigForm />)
  fireEvent.change(screen.getByPlaceholderText('e.g. NVDA'), {
    target: { value: 'AAPL' },
  })
  fireEvent.change(screen.getByLabelText(/trade date/i), {
    target: { value: '2024-05-10' },
  })
  fireEvent.change(screen.getByLabelText(/initial cash/i), {
    target: { value: '75000' },
  })
  fireEvent.change(screen.getByLabelText(/slippage \(bps\)/i), {
    target: { value: '2.5' },
  })
  fireEvent.change(screen.getByLabelText(/fee per trade/i), {
    target: { value: '0.5' },
  })
  fireEvent.change(screen.getByLabelText(/max position size/i), {
    target: { value: '25' },
  })

  fireEvent.click(screen.getByText(/run analysis/i))

  await waitFor(() => expect(createRun).toHaveBeenCalled())
  expect(createRun).toHaveBeenCalledWith(
    expect.objectContaining({
      simulation_config: expect.objectContaining({
        initial_cash: 75000,
        slippage_bps: 2.5,
        fee_per_trade: 0.5,
        max_position_pct: 25, // percent, not 0.25
      }),
    }),
  )
})

test('invalid simulation values block submit and show inline errors', async () => {
  render(<RunConfigForm />)
  fireEvent.change(screen.getByPlaceholderText('e.g. NVDA'), {
    target: { value: 'AAPL' },
  })
  fireEvent.change(screen.getByLabelText(/trade date/i), {
    target: { value: '2024-05-10' },
  })
  fireEvent.change(screen.getByLabelText(/initial cash/i), {
    target: { value: '0' },
  })
  fireEvent.change(screen.getByLabelText(/slippage \(bps\)/i), {
    target: { value: '-1' },
  })
  fireEvent.change(screen.getByLabelText(/fee per trade/i), {
    target: { value: '-0.1' },
  })
  fireEvent.change(screen.getByLabelText(/max position size/i), {
    target: { value: '101' },
  })

  fireEvent.click(screen.getByText(/run analysis/i))

  expect(createRun).not.toHaveBeenCalled()
  expect(screen.getByText(/initial cash \(\$\) must be greater than 0/i)).toBeInTheDocument()
  expect(screen.getByText(/slippage \(bps\) must be 0 or greater/i)).toBeInTheDocument()
  expect(screen.getByText(/fee per trade \(\$\) must be 0 or greater/i)).toBeInTheDocument()
  expect(screen.getByText(/max position size \(%\) must be between 0 and 100/i)).toBeInTheDocument()
})

test('maps API 422 simulation_config errors to field-level messages', async () => {
  jest.mocked(createRun).mockRejectedValueOnce(
    new ApiError('API error 422: /api/runs', 422, '/api/runs', [
      { loc: ['body', 'simulation_config', 'max_position_pct'], msg: 'Max Position Size must be between 0 and 100%' },
    ]),
  )

  render(<RunConfigForm />)
  fireEvent.change(screen.getByPlaceholderText('e.g. NVDA'), {
    target: { value: 'AAPL' },
  })
  fireEvent.change(screen.getByLabelText(/trade date/i), {
    target: { value: '2024-05-10' },
  })
  fireEvent.click(screen.getByText(/run analysis/i))

  await waitFor(() =>
    expect(screen.getByText(/please correct the highlighted simulation fields/i)).toBeInTheDocument(),
  )
  expect(screen.getByText(/max position size must be between 0 and 100%/i)).toBeInTheDocument()
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
