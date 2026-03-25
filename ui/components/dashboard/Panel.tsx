import type { ReactNode } from 'react'

type PanelProps = {
  title?: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
}

export default function Panel({
  title,
  subtitle,
  actions,
  children,
  className = '',
  contentClassName = '',
}: PanelProps) {
  return (
    <section className={`ws-panel ${className}`.trim()}>
      {(title || subtitle || actions) && (
        <header className="ws-panel-header">
          <div className="min-w-0">
            {title && <h2 className="ws-panel-title">{title}</h2>}
            {subtitle && <p className="ws-panel-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      <div className={`ws-panel-content ${contentClassName}`.trim()}>{children}</div>
    </section>
  )
}
