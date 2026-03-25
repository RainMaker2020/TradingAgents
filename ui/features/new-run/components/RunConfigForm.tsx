'use client'
import { useState } from 'react'
import AnalystSelector from './AnalystSelector'
import { useRunSubmit } from '../hooks/useRunSubmit'
import { DEFAULT_FORM } from '../types'
import type { NewRunFormState } from '../types'
import Panel from '@/components/dashboard/Panel'
import Toolbar, { ToolbarField } from '@/components/dashboard/Toolbar'
import SegmentedControl from '@/components/dashboard/SegmentedControl'
import { RUN_LIMITS } from '@/lib/defaults'

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label
      className="block mb-1.5 text-[10px] font-bold uppercase tracking-widest"
      style={{ color: 'var(--text-mid)', fontFamily: 'var(--font-mono)', letterSpacing: '0.1em' }}
    >
      {children}
    </label>
  )
}

export default function RunConfigForm() {
  const [form, setForm] = useState<NewRunFormState>(DEFAULT_FORM)
  const [activePreset, setActivePreset] = useState<'fast' | 'balanced' | 'deep' | null>(null)
  const { submit, loading, error } = useRunSubmit()
  const set = (k: keyof NewRunFormState, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }))

  const setPreset = (preset: 'balanced' | 'deep' | 'fast') => {
    setActivePreset(preset)
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
  const today = new Date().toISOString().slice(0, 10)

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); submit(form) }}
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
                style={activePreset === p ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : undefined}
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
        subtitle="Select the security and trade date"
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <FieldLabel>Ticker Symbol</FieldLabel>
            <input
              className="vault-input terminal-text font-bold text-sm tracking-widest"
              placeholder="e.g. NVDA"
              value={form.ticker}
              onChange={(e) => set('ticker', e.target.value.toUpperCase())}
              required
              pattern="[A-Z]{1,10}"
              title="1–10 uppercase letters"
              style={{ letterSpacing: '0.12em' }}
            />
          </div>
          <div>
            <FieldLabel>Trade Date</FieldLabel>
            <input
              id="trade-date"
              type="date"
              className="vault-input terminal-text text-sm"
              value={form.date}
              onChange={(e) => set('date', e.target.value)}
              required
              min="2020-01-01"
              max={today}
            />
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
              onChange={(id) => set('llm_provider', id)}
              segments={[
                { id: 'openai', label: 'OpenAI' },
                { id: 'anthropic', label: 'Anthropic' },
                { id: 'google', label: 'Google' },
              ]}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel>Deep Think LLM</FieldLabel>
              <input
                className="vault-input terminal-text text-[12px]"
                value={form.deep_think_llm}
                onChange={(e) => set('deep_think_llm', e.target.value)}
              />
            </div>
            <div>
              <FieldLabel>Quick Think LLM</FieldLabel>
              <input
                className="vault-input terminal-text text-[12px]"
                value={form.quick_think_llm}
                onChange={(e) => set('quick_think_llm', e.target.value)}
              />
            </div>
            <div>
              <FieldLabel>Debate Rounds</FieldLabel>
              <input
                type="number"
                min={RUN_LIMITS.minRounds}
                max={RUN_LIMITS.maxRounds}
                className="vault-input terminal-text"
                value={form.max_debate_rounds}
                onChange={(e) => set('max_debate_rounds', Number(e.target.value))}
              />
            </div>
            <div>
              <FieldLabel>Risk Discussion Rounds</FieldLabel>
              <input
                type="number"
                min={RUN_LIMITS.minRounds}
                max={RUN_LIMITS.maxRounds}
                className="vault-input terminal-text"
                value={form.max_risk_discuss_rounds}
                onChange={(e) => set('max_risk_discuss_rounds', Number(e.target.value))}
              />
            </div>
          </div>
        </div>
      </Panel>

      <Panel
        title="Active Analysts"
        subtitle="Select AI analysts for this run"
      >
        <AnalystSelector
          selected={form.enabled_analysts}
          onChange={(v) => set('enabled_analysts', v)}
        />
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

        {noAnalysts && (
          <span className="text-xs" style={{ color: 'var(--error)', fontFamily: 'var(--font-mono)' }}>
            Select at least one analyst
          </span>
        )}
        <button
          type="submit"
          disabled={loading || noAnalysts}
          className="btn-primary"
          style={{ minWidth: '160px', justifyContent: 'center', opacity: noAnalysts ? 0.45 : 1 }}
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
