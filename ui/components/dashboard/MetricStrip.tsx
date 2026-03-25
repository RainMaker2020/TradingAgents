type MetricItem = {
  label: string
  value: string
  tone?: 'neutral' | 'positive' | 'negative' | 'warning' | 'accent'
}

const toneClass: Record<NonNullable<MetricItem['tone']>, string> = {
  neutral: 'ws-metric-value-neutral',
  positive: 'ws-metric-value-positive',
  negative: 'ws-metric-value-negative',
  warning: 'ws-metric-value-warning',
  accent: 'ws-metric-value-accent',
}

export default function MetricStrip({ items }: { items: MetricItem[] }) {
  return (
    <div className="ws-metric-strip">
      {items.map((item) => (
        <article key={item.label} className="ws-metric-card">
          <p className="ws-metric-label">{item.label}</p>
          <p className={`ws-metric-value ${toneClass[item.tone ?? 'neutral']}`.trim()}>
            {item.value}
          </p>
        </article>
      ))}
    </div>
  )
}
