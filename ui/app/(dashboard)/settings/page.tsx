import SettingsForm from '@/features/settings/components/SettingsForm'
import MetricStrip from '@/components/dashboard/MetricStrip'
import Panel from '@/components/dashboard/Panel'

export default function SettingsPage() {
  return (
    <>
      <div className="ws-page-header">
        <div>
          <div className="apex-label" style={{ color: 'var(--accent)', opacity: 0.7 }}>
            Workspace Administration
          </div>
          <h1 className="ws-page-title">Settings</h1>
          <p className="ws-page-subtitle">Manage default model strategy and analysis behavior for operator workflows.</p>
        </div>
      </div>

      <MetricStrip
        items={[
          { label: 'Profiles', value: 'Default', tone: 'accent' },
          { label: 'Debate Cap', value: '5', tone: 'warning' },
          { label: 'Risk Cap', value: '5', tone: 'warning' },
          { label: 'Secrets Mode', value: '.env', tone: 'neutral' },
        ]}
      />

      <div className="ws-grid-2">
        <SettingsForm />
        <div className="space-y-3">
          <Panel title="Configuration Notes" subtitle="Operational guidance">
            <ul className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
              <li>Use lower-latency models for frequent intraday workflows.</li>
              <li>Increase debate rounds for higher uncertainty instruments.</li>
              <li>Keep defaults conservative for predictable operator behavior.</li>
              <li>Update server secrets in environment config, not this dashboard.</li>
            </ul>
          </Panel>
          <Panel title="Change Policy" subtitle="When to adjust defaults">
            <ul className="space-y-2 text-[12px]" style={{ color: 'var(--text-mid)' }}>
              <li>After model upgrades or provider changes.</li>
              <li>When run completion time exceeds workflow targets.</li>
              <li>When output quality degrades in run history reviews.</li>
            </ul>
          </Panel>
        </div>
      </div>
    </>
  )
}
