'use client'
import { useEffect, useRef } from 'react'

interface AbortConfirmModalProps {
  open: boolean
  ticker: string
  onConfirm: () => void
  onCancel: () => void
}

export default function AbortConfirmModal({ open, ticker, onConfirm, onCancel }: AbortConfirmModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  const confirmRef = useRef<HTMLButtonElement>(null)

  // Focus trap: focus Cancel button when modal opens
  useEffect(() => {
    if (open) cancelRef.current?.focus()
  }, [open])

  // ESC key closes modal; Tab/Shift-Tab trapped within the two buttons
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onCancel(); return }
      if (e.key === 'Tab') {
        e.preventDefault()
        if (e.shiftKey) {
          // Shift+Tab cycles backwards: if on Cancel, go to Abort; if on Abort, go to Cancel
          if (document.activeElement === cancelRef.current) {
            confirmRef.current?.focus()
          } else {
            cancelRef.current?.focus()
          }
        } else {
          // Tab cycles forward: if on Abort, go back to Cancel; if on Cancel, go to Abort
          if (document.activeElement === confirmRef.current) {
            cancelRef.current?.focus()
          } else {
            confirmRef.current?.focus()
          }
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="abort-modal-title"
      style={{
        position: 'fixed', inset: 0, zIndex: 50,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.6)',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onCancel() }}
    >
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-raised)',
          borderRadius: '12px',
          padding: '24px',
          width: '360px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
        }}
      >
        <h2
          id="abort-modal-title"
          style={{
            fontSize: '16px', fontWeight: 600,
            color: 'var(--text-high)', marginBottom: '8px',
            fontFamily: 'var(--font-manrope)',
          }}
        >
          Abort analysis?
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-mid)', marginBottom: '20px', lineHeight: 1.5 }}>
          This will immediately stop the <strong style={{ color: 'var(--text-high)' }}>{ticker}</strong> run.
          Partial results are kept but cannot be resumed.
        </p>
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="btn-secondary"
            style={{ padding: '7px 16px', fontSize: '13px' }}
          >
            Cancel
          </button>
          <button
            ref={confirmRef}
            onClick={onConfirm}
            style={{
              background: 'var(--error)',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '7px 16px',
              fontSize: '13px',
              cursor: 'pointer',
              fontFamily: 'var(--font-manrope)',
              fontWeight: 600,
            }}
          >
            Abort run
          </button>
        </div>
      </div>
    </div>
  )
}
