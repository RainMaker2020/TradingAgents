'use client'
import { useEffect, useState } from 'react'
import { getSettings, updateSettings } from '@/lib/api-client'
import type { SettingsFormState } from '../types'
import Panel from '@/components/dashboard/Panel'
import Toolbar from '@/components/dashboard/Toolbar'
import { DEFAULT_WORKSPACE_SETTINGS, RUN_LIMITS } from '@/lib/defaults'

const DEFAULTS: SettingsFormState = { ...DEFAULT_WORKSPACE_SETTINGS }

export default function SettingsForm() {
  const [form, setForm]   = useState<SettingsFormState>(DEFAULTS)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const set = (k: keyof SettingsFormState, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }))

  useEffect(() => {
    getSettings()
      .then(setForm)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaveError(null)
    try {
      await updateSettings(form)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save settings')
    }
  }

  return (
    <form onSubmit={save} className="space-y-3">
      <Toolbar
        left={
          <span className="terminal-text text-[10px]" style={{ color: 'var(--text-low)', letterSpacing: '0.08em' }}>
            WORKSPACE DEFAULTS
          </span>
        }
        right={
          <span className="terminal-text text-[10px]" style={{ color: loading ? 'var(--hold)' : 'var(--buy)', letterSpacing: '0.08em' }}>
            {loading ? 'LOADING' : 'SYNCED'}
          </span>
        }
      />

      <Panel title="Model Configuration" subtitle="Provider model aliases used at runtime">
        <div>
          <label className="block text-xs mb-2 capitalize" style={{ color: 'var(--text-mid)' }}>
            llm provider
          </label>
          <select className="vault-input" value={form.llm_provider} onChange={(e) => set('llm_provider', e.target.value)}>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="google">Google</option>
          </select>
        </div>
        {(['deep_think_llm', 'quick_think_llm'] as const).map((key) => (
          <div key={key}>
            <label className="block text-xs mb-2 capitalize" style={{ color: 'var(--text-mid)' }}>
              {key.replace(/_/g, ' ')}
            </label>
            <input
              className="vault-input"
              value={form[key]}
              onChange={(e) => set(key, e.target.value)}
            />
          </div>
        ))}
      </Panel>

      <Panel title="Analysis Parameters" subtitle="Discussion depth controls">
        {(['max_debate_rounds', 'max_risk_discuss_rounds'] as const).map((key) => (
          <div key={key}>
            <label className="block text-xs mb-2 capitalize" style={{ color: 'var(--text-mid)' }}>
              {key.replace(/_/g, ' ')}
            </label>
            <input
              type="number" min={RUN_LIMITS.minRounds} max={RUN_LIMITS.maxRounds}
              className="vault-input"
              value={form[key]}
              onChange={(e) => set(key, Number(e.target.value))}
            />
          </div>
        ))}
      </Panel>

      {/* ── Security notice ─────────────────────────────────────── */}
      <div className="rounded-lg px-5 py-3.5 text-xs leading-relaxed" style={{ background: 'var(--bg-elevated)', color: 'var(--text-mid)', border: '1px solid var(--border)' }}>
        API keys and secrets are configured via <code style={{ color: 'var(--accent-light)' }} className="font-mono">.env</code> on the server and are not editable here.
      </div>

      {/* ── Save error ──────────────────────────────────────────── */}
      {saveError && (
        <div
          className="px-4 py-3 rounded-xl text-sm"
          style={{
            background: 'var(--error-bg)',
            color: 'var(--error)',
            border: '1px solid rgba(255,43,62,0.25)',
          }}
        >
          {saveError}
        </div>
      )}

      {/* ── Actions ─────────────────────────────────────────────── */}
      <div className="flex gap-3 justify-end pt-1">
        <button
          type="button"
          onClick={() => setForm(DEFAULTS)}
          className="btn-secondary px-4 py-2.5 text-sm"
        >
          Reset to Defaults
        </button>
        <button
          type="submit"
          className="btn-primary px-5 py-2.5 text-sm"
        >
          {saved ? '✓ Saved' : 'Save Changes'}
        </button>
      </div>
    </form>
  )
}
