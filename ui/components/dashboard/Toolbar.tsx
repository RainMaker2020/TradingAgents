import type { ReactNode } from 'react'

export default function Toolbar({
  left,
  right,
  className = '',
}: {
  left?: ReactNode
  right?: ReactNode
  className?: string
}) {
  return (
    <div className={`ws-toolbar ${className}`.trim()}>
      <div className="ws-toolbar-left">{left}</div>
      <div className="ws-toolbar-right">{right}</div>
    </div>
  )
}

export function ToolbarField({
  label,
  children,
}: {
  label?: string
  children: ReactNode
}) {
  return (
    <label className="ws-toolbar-field">
      {label && <span className="ws-toolbar-label">{label}</span>}
      {children}
    </label>
  )
}
