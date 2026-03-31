import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import SettingsForm from '@/features/settings/components/SettingsForm'
import { getProviderModels, getSettings } from '@/lib/api-client'

jest.mock('@/lib/api-client', () => ({
  getSettings: jest.fn().mockResolvedValue({
    llm_provider: 'openai',
    deep_think_llm: 'gpt-5.2',
    quick_think_llm: 'gpt-5-mini',
    max_debate_rounds: 1,
    max_risk_discuss_rounds: 1,
    execution_mode: 'graph',
    profile_preset: null,
  }),
  getProviderModels: jest.fn().mockResolvedValue({ provider: 'openai', models: [], error: null }),
  updateSettings: jest.fn().mockResolvedValue({}),
}))

test('loads settings with deepseek provider', async () => {
  jest.mocked(getSettings).mockResolvedValueOnce({
    llm_provider: 'deepseek',
    deep_think_llm: 'deepseek-reasoner',
    quick_think_llm: 'deepseek-chat',
    max_debate_rounds: 2,
    max_risk_discuss_rounds: 2,
    execution_mode: 'graph',
    profile_preset: 'balanced',
  })
  jest.mocked(getProviderModels).mockResolvedValueOnce({
    provider: 'deepseek',
    models: ['deepseek-chat', 'deepseek-reasoner'],
    error: null,
  })

  render(<SettingsForm />)

  // Saved values must be preserved — not overwritten by defaults
  await waitFor(() => {
    expect(screen.getByDisplayValue('DeepSeek')).toBeInTheDocument()
  })
  expect(screen.getByDisplayValue('deepseek-reasoner')).toBeInTheDocument()
  expect(screen.getByDisplayValue('deepseek-chat')).toBeInTheDocument()
})

test('switches to deepseek defaults', async () => {
  render(<SettingsForm />)

  // Wait for initial OpenAI settings to load
  await waitFor(() => {
    expect(screen.getByDisplayValue('OpenAI')).toBeInTheDocument()
  })

  fireEvent.change(screen.getByDisplayValue('OpenAI'), {
    target: { value: 'deepseek' },
  })

  // After event settles, all three fields consistent with DeepSeek defaults.
  // No stale OpenAI model name should remain selected.
  await waitFor(() => {
    expect(screen.getByDisplayValue('deepseek-reasoner')).toBeInTheDocument()
  })
  expect(screen.getByDisplayValue('DeepSeek')).toBeInTheDocument()
  expect(screen.getByDisplayValue('deepseek-chat')).toBeInTheDocument()
  expect(screen.queryByDisplayValue('gpt-5.2')).not.toBeInTheDocument()
})

test('shows DeepSeek defaults when model fetch fails', async () => {
  jest.mocked(getProviderModels)
    .mockResolvedValueOnce({ provider: 'openai', models: [], error: null }) // initial openai load
    .mockRejectedValueOnce(new Error('No API key'))                          // deepseek fetch fails

  render(<SettingsForm />)

  await waitFor(() => {
    expect(screen.getByDisplayValue('OpenAI')).toBeInTheDocument()
  })

  fireEvent.change(screen.getByDisplayValue('OpenAI'), {
    target: { value: 'deepseek' },
  })

  // After failed fetch settles: defaults remain, warning renders
  await waitFor(() => {
    expect(screen.getByText(/model list:/i)).toBeInTheDocument()
  })
  expect(screen.getByDisplayValue('DeepSeek')).toBeInTheDocument()
  expect(screen.getByDisplayValue('deepseek-reasoner')).toBeInTheDocument()
  expect(screen.getByDisplayValue('deepseek-chat')).toBeInTheDocument()
})
