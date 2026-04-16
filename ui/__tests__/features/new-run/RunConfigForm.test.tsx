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
    getSettings: jest.fn().mockResolvedValue({
      llm_provider: 'openai',
      deep_think_llm: 'gpt-5.2',
      quick_think_llm: 'gpt-5-mini',
      max_debate_rounds: 1,
      max_risk_discuss_rounds: 1,
      execution_mode: 'graph',
      profile_preset: null,
    }),
    updateSettings: jest.fn().mockImplementation((s: unknown) => Promise.resolve(s)),
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
  expect(screen.getByPlaceholderText(/e\.g\. NVDA/i)).toBeInTheDocument()
  expect(screen.getByLabelText(/trade date/i)).toBeInTheDocument()
})

test('submitting navigates to run detail page', async () => {
  render(<RunConfigForm />)
  fireEvent.change(screen.getByPlaceholderText(/e\.g\. NVDA/i), {
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
  fireEvent.change(screen.getByPlaceholderText(/e\.g\. NVDA/i), {
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

test('submits backtest mode with end_date', async () => {
  render(<RunConfigForm />)
  fireEvent.click(screen.getByRole('tab', { name: /backtest \(engine\)/i }))
  fireEvent.change(screen.getByPlaceholderText(/e\.g\. NVDA/i), {
    target: { value: 'AAPL' },
  })
  fireEvent.change(screen.getByLabelText(/trade date/i), {
    target: { value: '2024-01-02' },
  })
  fireEvent.change(screen.getByLabelText(/end date/i), {
    target: { value: '2024-01-10' },
  })

  fireEvent.click(screen.getByText(/run analysis/i))

  await waitFor(() => expect(createRun).toHaveBeenCalled())
  expect(createRun).toHaveBeenCalledWith(
    expect.objectContaining({
      mode: 'backtest',
      end_date: '2024-01-10',
      ticker: 'AAPL',
      date: '2024-01-02',
    }),
  )
})

test('invalid simulation values block submit and show inline errors', async () => {
  render(<RunConfigForm />)
  fireEvent.change(screen.getByPlaceholderText(/e\.g\. NVDA/i), {
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
      { loc: ['body', 'simulation_config', 'max_position_pct'], msg: 'max_position_pct (percent of equity) must be greater than 0 and at most 100' },
    ]),
  )

  render(<RunConfigForm />)
  fireEvent.change(screen.getByPlaceholderText(/e\.g\. NVDA/i), {
    target: { value: 'AAPL' },
  })
  fireEvent.change(screen.getByLabelText(/trade date/i), {
    target: { value: '2024-05-10' },
  })
  fireEvent.click(screen.getByText(/run analysis/i))

  await waitFor(() =>
    expect(screen.getByText(/please correct the highlighted simulation fields/i)).toBeInTheDocument(),
  )
  expect(screen.getByText(/max_position_pct.*percent of equity/i)).toBeInTheDocument()
})

test('switches to deepseek defaults', async () => {
  render(<RunConfigForm />)

  fireEvent.click(screen.getByRole('tab', { name: 'DeepSeek' }))

  // After event settles, all three fields must be consistent with DeepSeek defaults.
  // No stale OpenAI model name should remain selected.
  await waitFor(() => {
    expect(screen.getByDisplayValue('deepseek-reasoner')).toBeInTheDocument()
    expect(screen.getByDisplayValue('deepseek-chat')).toBeInTheDocument()
    expect(screen.queryByDisplayValue('gpt-5.2')).not.toBeInTheDocument()
  })
})

test('shows DeepSeek defaults when model fetch fails', async () => {
  jest.mocked(getProviderModels).mockImplementation((provider: string) => {
    if (provider === 'deepseek') {
      return Promise.resolve({ provider: 'deepseek', models: [], error: 'No API key' })
    }
    return Promise.resolve({ provider: 'openai', models: ['gpt-5-mini'], error: null })
  })

  render(<RunConfigForm />)

  fireEvent.click(screen.getByRole('tab', { name: 'DeepSeek' }))

  await waitFor(() => {
    expect(screen.getByText(/model list:/i)).toBeInTheDocument()
    expect(screen.getByText(/No API key/i)).toBeInTheDocument()
  })
})
