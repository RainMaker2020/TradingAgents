'use client'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import AnalystSelector from './AnalystSelector'
import { useRunSubmit } from '../hooks/useRunSubmit'
import { DEFAULT_FORM } from '../types'
import type { NewRunFormState } from '../types'
import Panel from '@/components/dashboard/Panel'
import Toolbar, { ToolbarField } from '@/components/dashboard/Toolbar'
import SegmentedControl from '@/components/dashboard/SegmentedControl'
import { inferProfileFromRounds, RUN_LIMITS, PROVIDER_MODEL_DEFAULTS } from '@/lib/defaults'
import { getProviderModels, getSettings, updateSettings } from '@/lib/api-client'
import {
  validateRunTarget,
  validateSimulationConfig,
  type RunTargetErrors,
  type SimulationErrors,
} from '../validation'

function FieldLabel({
  children,
  htmlFor,
}: {
  children: React.ReactNode
  htmlFor?: string
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="block mb-1.5 text-[10px] font-bold uppercase tracking-widest"
      style={{ color: 'var(--text-mid)', fontFamily: 'var(--font-mono)', letterSpacing: '0.1em' }}
    >
      {children}
    </label>
  )
}

type RunConfigFormProps = {
  /** Notifies parent (e.g. sidebar copy) when mode changes or hydrates from settings. */
  onExecutionModeChange?: (mode: 'graph' | 'backtest') => void
}

export default function RunConfigForm({ onExecutionModeChange }: RunConfigFormProps = {}) {
  const [form, setForm] = useState<NewRunFormState>(DEFAULT_FORM)
  const [simulationErrors, setSimulationErrors] = useState<SimulationErrors>({})
  const [runTargetErrors, setRunTargetErrors] = useState<RunTargetErrors>({})
  const [prefsHydrated, setPrefsHydrated] = useState(false)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [autosaveError, setAutosaveError] = useState<string | null>(null)
  /** If the user changes LLM fields before getSettings() resolves, do not overwrite their choice. */
  const userOverrodeLlmRef = useRef(false)
  /** If the user changes mode/debate/risk fields before getSettings() resolves, do not overwrite their choice. */
  const userOverrodePrefsRef = useRef(false)
  const [modelsLoading, setModelsLoading] = useState(true)
  const [modelsError, setModelsError] = useState<string | null>(null)
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const { submit, loading, error } = useRunSubmit()
  const set = <K extends keyof NewRunFormState>(k: K, v: NewRunFormState[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  const profileHighlight = inferProfileFromRounds(form.max_debate_rounds)

  useEffect(() => {
    let cancelled = false
    getSettings()
      .then((s) => {
        if (cancelled) return
        setForm((f) => {
          const withLlm = userOverrodeLlmRef.current ? f : {
            ...f,
            llm_provider: s.llm_provider,
            deep_think_llm: s.deep_think_llm,
            quick_think_llm: s.quick_think_llm,
          }
          const withPrefs = userOverrodePrefsRef.current ? withLlm : {
            ...withLlm,
            max_debate_rounds: s.max_debate_rounds,
            max_risk_discuss_rounds: s.max_risk_discuss_rounds,
            mode: s.execution_mode,
          }
          return withPrefs
        })
      })
      .catch((err) => {
        if (!cancelled) setSettingsError(err instanceof Error ? err.message : 'Failed to load settings')
      })
      .finally(() => {
        if (!cancelled) setPrefsHydrated(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useLayoutEffect(() => {
    onExecutionModeChange?.(form.mode)
  }, [form.mode, onExecutionModeChange])

  useEffect(() => {
    if (!prefsHydrated) return
    const t = setTimeout(() => {
      void updateSettings({
        llm_provider: form.llm_provider,
        deep_think_llm: form.deep_think_llm,
        quick_think_llm: form.quick_think_llm,
        max_debate_rounds: form.max_debate_rounds,
        max_risk_discuss_rounds: form.max_risk_discuss_rounds,
        execution_mode: form.mode,
        profile_preset: profileHighlight,
      }).then(() => {
        setAutosaveError(null)
      }).catch((err) => {
        setAutosaveError(err instanceof Error ? err.message : 'Auto-save failed')
      })
    }, 500)
    return () => clearTimeout(t)
  }, [
    prefsHydrated,
    form.llm_provider,
    form.deep_think_llm,
    form.quick_think_llm,
    form.max_debate_rounds,
    form.max_risk_discuss_rounds,
    form.mode,
    profileHighlight,
  ])

  const parseNumericInput = (value: string): number =>
    value.trim() === '' ? Number.NaN : Number(value)

  useEffect(() => {
    let active = true
    getProviderModels(form.llm_provider)
      .then((resp) => {
        if (!active) return
        setAvailableModels(resp.models)
        setModelsError(resp.error)
      })
      .catch((err) => {
        if (!active) return
        setAvailableModels([])
        setModelsError(err instanceof Error ? err.message : 'Failed to load models')
      })
      .finally(() => {
        if (active) setModelsLoading(false)
      })
    return () => {
      active = false
    }
  }, [form.llm_provider])

  const modelOptions = Array.from(
    new Set([
      ...availableModels,
      form.deep_think_llm,
      form.quick_think_llm,
    ].filter(Boolean)),
  )

  const markPrefsOverridden = () => {
    if (!userOverrodePrefsRef.current) {
      userOverrodePrefsRef.current = true
      setSettingsError(null)
    }
  }

  const setPreset = (preset: 'balanced' | 'deep' | 'fast') => {
    markPrefsOverridden()
    if (preset === 'deep') {
      setForm((f) => ({ ...f, max_debate_rounds: 3, max_risk_discuss_rounds: 3 }))
      return
    }
    if (preset === 'fast') {
      setForm((f) => ({ ...f, max_debate_rounds: 1, max_risk_discuss_rounds: 1 }))
      return
    }
    setForm((f) => ({ ...f, max_debate_rounds: 2, max_risk_discuss_rounds: 2 }))
  }

  const noAnalysts = form.enabled_analysts.length === 0
  const graphModeNeedsAnalysts = form.mode === 'graph' && noAnalysts
  const today = new Date().toISOString().slice(0, 10)
  const hasSimulationErrors = Object.keys(simulationErrors).length > 0
  /** Block Run while server-mapped or client-shown simulation field errors exist; target/LLM rules run on each submit. */
  const cannotSubmit = hasSimulationErrors

  return (
    <form
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        const targetErr = validateRunTarget(form)
        const simErr = validateSimulationConfig(form)
        setRunTargetErrors(targetErr)
        setSimulationErrors(simErr)
        if (Object.keys(targetErr).length > 0 || Object.keys(simErr).length > 0) return
        submit(form, setSimulationErrors)
      }}
      className="space-y-3"
    >
      <Toolbar
        left={
          <ToolbarField label="Profile">
            {(['fast', 'balanced', 'deep'] as const).map((p) => (
              <button
                key={p}
                type="button"
                className="btn-secondary !h-[34px] !px-3 !py-0 text-xs"
                style={profileHighlight === p ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : undefined}
                onClick={() => setPreset(p)}
              >
                {p === 'fast' ? 'Fast' : p === 'balanced' ? 'Balanced' : 'Deep Research'}
              </button>
            ))}
          </ToolbarField>
        }
        right={
          <span className="terminal-text text-[10px]" style={{ color: 'var(--text-low)', letterSpacing: '0.06em' }}>
            LAUNCH PAD
          </span>
        }
      />

      {settingsError && (
        <div className="px-4 py-2 rounded-lg text-xs" style={{ background: 'var(--error-bg)', color: 'var(--error)', border: '1px solid rgba(255,43,62,0.25)' }}>
          Settings: {settingsError}
        </div>
      )}

      {autosaveError && (
        <div className="px-4 py-2 rounded-lg text-xs" style={{ background: 'var(--error-bg)', color: 'var(--error)', border: '1px solid rgba(255,43,62,0.25)' }}>
          Auto-save: {autosaveError}
        </div>
      )}

      {/* Error */}
      {error && (
        <div
          className="px-4 py-3 rounded-xl text-sm flex items-center gap-2.5"
          style={{
            background: 'var(--error-bg)',
            color: 'var(--error)',
            border: '1px solid rgba(255,43,62,0.25)',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.4"/>
            <path d="M7 4v4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            <circle cx="7" cy="10" r="0.8" fill="currentColor"/>
          </svg>
          {error}
        </div>
      )}

      <Panel
        title="Analysis Target"
        subtitle="Select execution mode, symbol, and dates"
      >
        <div className="space-y-4">
          <div>
            <FieldLabel>Execution Mode</FieldLabel>
            <SegmentedControl
              ariaLabel="Execution mode"
              activeId={form.mode}
              onChange={(id) => {
                markPrefsOverridden()
                const next = id === 'backtest' ? 'backtest' : 'graph'
                set('mode', next)
                onExecutionModeChange?.(next)
                if (runTargetErrors.end_date) {
                  setRunTargetErrors((prev) => ({ ...prev, end_date: undefined }))
                }
              }}
              segments={[
                { id: 'graph', label: 'Graph (LLM)' },
                { id: 'backtest', label: 'Backtest (Engine)' },
              ]}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="ticker-symbol">Ticker Symbol</FieldLabel>
            <input
              id="ticker-symbol"
              className="vault-input terminal-text font-bold text-sm tracking-widest"
              placeholder="e.g. NVDA, BTC-USD"
              value={form.ticker}
              onChange={(e) => {
                set('ticker', e.target.value.toUpperCase())
                if (runTargetErrors.ticker) {
                  setRunTargetErrors((prev) => ({ ...prev, ticker: undefined }))
                }
              }}
              aria-invalid={Boolean(runTargetErrors.ticker)}
              aria-describedby={runTargetErrors.ticker ? 'ticker-symbol-error' : undefined}
              required
              pattern="[\^A-Z0-9.\-=_]{1,63}"
              title="Yahoo symbol: up to 63 chars; A–Z 0-9 . - ^ = _"
              style={{ letterSpacing: '0.12em' }}
            />
            {runTargetErrors.ticker && (
              <p
                id="ticker-symbol-error"
                className="text-[10px] mt-1"
                style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}
                role="alert"
              >
                {runTargetErrors.ticker}
              </p>
            )}
          </div>
          <div>
            <FieldLabel htmlFor="trade-date">Trade Date</FieldLabel>
            <input
              id="trade-date"
              type="date"
              className="vault-input terminal-text text-sm"
              value={form.date}
              onChange={(e) => {
                set('date', e.target.value)
                if (runTargetErrors.date) {
                  setRunTargetErrors((prev) => ({ ...prev, date: undefined }))
                }
              }}
              aria-invalid={Boolean(runTargetErrors.date)}
              aria-describedby={runTargetErrors.date ? 'trade-date-error' : undefined}
              required
              min="2020-01-01"
              max={today}
            />
            {runTargetErrors.date && (
              <p
                id="trade-date-error"
                className="text-[10px] mt-1"
                style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}
                role="alert"
              >
                {runTargetErrors.date}
              </p>
            )}
          </div>
          {form.mode === 'backtest' && (
            <div>
              <FieldLabel htmlFor="end-date">End Date</FieldLabel>
              <input
                id="end-date"
                type="date"
                className="vault-input terminal-text text-sm"
                value={form.end_date}
                onChange={(e) => {
                  set('end_date', e.target.value)
                  if (runTargetErrors.end_date) {
                    setRunTargetErrors((prev) => ({ ...prev, end_date: undefined }))
                  }
                }}
                aria-invalid={Boolean(runTargetErrors.end_date)}
                aria-describedby={runTargetErrors.end_date ? 'end-date-error' : undefined}
                min={form.date || '2020-01-01'}
                max={today}
              />
              {runTargetErrors.end_date && (
                <p
                  id="end-date-error"
                  className="text-[10px] mt-1"
                  style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}
                  role="alert"
                >
                  {runTargetErrors.end_date}
                </p>
              )}
            </div>
          )}
          </div>
        </div>
      </Panel>

      <Panel
        title="Model Configuration"
        subtitle="LLM provider and reasoning models"
      >
        <div className="space-y-4">
          <div>
            <FieldLabel>LLM Provider</FieldLabel>
            <SegmentedControl
              ariaLabel="LLM provider"
              activeId={form.llm_provider}
              onChange={(id) => {
                userOverrodeLlmRef.current = true
                const defaults = PROVIDER_MODEL_DEFAULTS[id] ?? PROVIDER_MODEL_DEFAULTS['openai']
                setModelsLoading(true)
                setModelsError(null)
                setForm((f) => ({
                  ...f,
                  llm_provider: id,
                  deep_think_llm: defaults.deep,
                  quick_think_llm: defaults.quick,
                }))
              }}
              segments={[
                { id: 'openai', label: 'OpenAI' },
                { id: 'anthropic', label: 'Anthropic' },
                { id: 'google', label: 'Google' },
                { id: 'deepseek', label: 'DeepSeek' },
              ]}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel>Deep Think LLM</FieldLabel>
              <select
                className="vault-input terminal-text text-[12px]"
                value={form.deep_think_llm}
                onChange={(e) => {
                  userOverrodeLlmRef.current = true
                  set('deep_think_llm', e.target.value)
                }}
                disabled={modelsLoading && modelOptions.length === 0}
              >
                {modelOptions.length === 0 ? (
                  <option value={form.deep_think_llm}>
                    {modelsLoading ? 'Loading models...' : 'No models available'}
                  </option>
                ) : (
                  modelOptions.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div>
              <FieldLabel>Quick Think LLM</FieldLabel>
              <select
                className="vault-input terminal-text text-[12px]"
                value={form.quick_think_llm}
                onChange={(e) => {
                  userOverrodeLlmRef.current = true
                  set('quick_think_llm', e.target.value)
                }}
                disabled={modelsLoading && modelOptions.length === 0}
              >
                {modelOptions.length === 0 ? (
                  <option value={form.quick_think_llm}>
                    {modelsLoading ? 'Loading models...' : 'No models available'}
                  </option>
                ) : (
                  modelOptions.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div>
              <FieldLabel>Debate Rounds</FieldLabel>
              <input
                type="number"
                min={RUN_LIMITS.minRounds}
                max={RUN_LIMITS.maxRounds}
                step={1}
                className="vault-input terminal-text"
                value={Number.isFinite(form.max_debate_rounds) ? form.max_debate_rounds : ''}
                onChange={(e) => {
                  markPrefsOverridden()
                  set('max_debate_rounds', parseNumericInput(e.target.value))
                  if (runTargetErrors.max_debate_rounds) {
                    setRunTargetErrors((prev) => ({ ...prev, max_debate_rounds: undefined }))
                  }
                }}
                aria-invalid={Boolean(runTargetErrors.max_debate_rounds)}
                aria-describedby={
                  runTargetErrors.max_debate_rounds ? 'debate-rounds-error' : undefined
                }
              />
              {runTargetErrors.max_debate_rounds && (
                <p
                  id="debate-rounds-error"
                  className="text-[10px] mt-1"
                  style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}
                  role="alert"
                >
                  {runTargetErrors.max_debate_rounds}
                </p>
              )}
            </div>
            <div>
              <FieldLabel>Risk Discussion Rounds</FieldLabel>
              <input
                type="number"
                min={RUN_LIMITS.minRounds}
                max={RUN_LIMITS.maxRounds}
                step={1}
                className="vault-input terminal-text"
                value={Number.isFinite(form.max_risk_discuss_rounds) ? form.max_risk_discuss_rounds : ''}
                onChange={(e) => {
                  markPrefsOverridden()
                  set('max_risk_discuss_rounds', parseNumericInput(e.target.value))
                  if (runTargetErrors.max_risk_discuss_rounds) {
                    setRunTargetErrors((prev) => ({ ...prev, max_risk_discuss_rounds: undefined }))
                  }
                }}
                aria-invalid={Boolean(runTargetErrors.max_risk_discuss_rounds)}
                aria-describedby={
                  runTargetErrors.max_risk_discuss_rounds ? 'risk-rounds-error' : undefined
                }
              />
              {runTargetErrors.max_risk_discuss_rounds && (
                <p
                  id="risk-rounds-error"
                  className="text-[10px] mt-1"
                  style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}
                  role="alert"
                >
                  {runTargetErrors.max_risk_discuss_rounds}
                </p>
              )}
            </div>
          </div>
        </div>
      </Panel>
      {modelsError && (
        <p className="text-xs px-1" style={{ color: 'var(--hold)' }}>
          Model list: {modelsError}
        </p>
      )}

      {form.mode === 'graph' && (
        <Panel
          title="Active Analysts"
          subtitle="Select AI analysts for this run"
        >
          <AnalystSelector
            selected={form.enabled_analysts}
            onChange={(v) => set('enabled_analysts', v)}
          />
        </Panel>
      )}

      <Panel
        title="Simulation Parameters"
        subtitle="User-friendly units sent in simulation_config"
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="initial-cash">Initial Cash ($)</FieldLabel>
            <input
              id="initial-cash"
              type="number"
              min={1}
              step="1"
              className="vault-input terminal-text"
              value={Number.isNaN(form.initial_cash) ? '' : form.initial_cash}
              onChange={(e) => {
                set('initial_cash', parseNumericInput(e.target.value))
                if (simulationErrors.initial_cash) {
                  setSimulationErrors((prev) => ({ ...prev, initial_cash: undefined }))
                }
              }}
              required
            />
            {simulationErrors.initial_cash && (
              <p className="text-[10px] mt-1" style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}>
                {simulationErrors.initial_cash}
              </p>
            )}
          </div>
          <div>
            <FieldLabel htmlFor="slippage-bps">Slippage (bps)</FieldLabel>
            <input
              id="slippage-bps"
              type="number"
              min={0}
              step="0.1"
              className="vault-input terminal-text"
              value={Number.isNaN(form.slippage_bps) ? '' : form.slippage_bps}
              onChange={(e) => {
                set('slippage_bps', parseNumericInput(e.target.value))
                if (simulationErrors.slippage_bps) {
                  setSimulationErrors((prev) => ({ ...prev, slippage_bps: undefined }))
                }
              }}
              required
            />
            {simulationErrors.slippage_bps && (
              <p className="text-[10px] mt-1" style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}>
                {simulationErrors.slippage_bps}
              </p>
            )}
          </div>
          <div>
            <FieldLabel htmlFor="fee-per-trade">Fee Per Trade ($)</FieldLabel>
            <input
              id="fee-per-trade"
              type="number"
              min={0}
              step="0.01"
              className="vault-input terminal-text"
              value={Number.isNaN(form.fee_per_trade) ? '' : form.fee_per_trade}
              onChange={(e) => {
                set('fee_per_trade', parseNumericInput(e.target.value))
                if (simulationErrors.fee_per_trade) {
                  setSimulationErrors((prev) => ({ ...prev, fee_per_trade: undefined }))
                }
              }}
              required
            />
            {simulationErrors.fee_per_trade && (
              <p className="text-[10px] mt-1" style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}>
                {simulationErrors.fee_per_trade}
              </p>
            )}
          </div>
          <div>
            <FieldLabel htmlFor="max-position-pct">Max Position Size (%)</FieldLabel>
            <input
              id="max-position-pct"
              type="number"
              min={0.01}
              max={100}
              step="0.01"
              className="vault-input terminal-text"
              value={Number.isNaN(form.max_position_pct) ? '' : form.max_position_pct}
              onChange={(e) => {
                set('max_position_pct', parseNumericInput(e.target.value))
                if (simulationErrors.max_position_pct) {
                  setSimulationErrors((prev) => ({ ...prev, max_position_pct: undefined }))
                }
              }}
              required
            />
            {simulationErrors.max_position_pct && (
              <p className="text-[10px] mt-1" style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}>
                {simulationErrors.max_position_pct}
              </p>
            )}
            <p className="text-[10px] mt-1" style={{ color: 'var(--text-low)', fontFamily: 'var(--font-mono)' }}>
              Enter percent (example: 10 means 10%).
            </p>
          </div>
        </div>
      </Panel>

      {/* ── Submit ────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between pt-1 px-1">
        <div
          className="flex items-center gap-2 text-[10px]"
          style={{ color: 'var(--text-low)', fontFamily: 'var(--font-mono)', letterSpacing: '0.04em' }}
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1.2"/>
            <path d="M5 3v2.5l1.5 1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
          </svg>
          Duration varies by symbol, model, and debate depth
        </div>

        {graphModeNeedsAnalysts && (
          <span className="text-xs" style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}>
            Select at least one analyst
          </span>
        )}
        <button
          type="submit"
          disabled={loading || graphModeNeedsAnalysts || cannotSubmit}
          className="btn-primary"
          style={{
            minWidth: '160px',
            justifyContent: 'center',
            opacity: graphModeNeedsAnalysts || cannotSubmit ? 0.45 : 1,
          }}
        >
          {loading ? (
            <>
              <svg
                width="13"
                height="13"
                viewBox="0 0 13 13"
                fill="none"
                style={{ animation: 'spin-slow 0.7s linear infinite' }}
              >
                <circle cx="6.5" cy="6.5" r="5" stroke="rgba(0,0,0,0.25)" strokeWidth="1.5"/>
                <path d="M6.5 1.5a5 5 0 0 1 5 5" stroke="var(--bg-base)" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              Starting…
            </>
          ) : (
            <>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <polygon points="3,2 10,6 3,10" fill="var(--bg-base)"/>
              </svg>
              Run Analysis
            </>
          )}
        </button>
      </div>
    </form>
  )
}
