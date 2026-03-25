'use client'
import { useState } from 'react'
import { usePDF } from 'react-to-pdf'
import type { ChiefAnalystReport } from '@/lib/types/agents'
import type { StepStatus } from '@/lib/types/agents'
import type { AgentStep } from '@/lib/types/run'
import { deriveChiefReportViewModel } from './chiefReportDerivation'

type Props = {
  report: ChiefAnalystReport | null
  status: StepStatus
  ticker: string
  date: string
  reports: Partial<Record<AgentStep, string[]>>
  chiefRawReport?: string
}

const VERDICT_COLOR: Record<string, string> = {
  BUY: '#087f5b',
  SELL: '#b42318',
  HOLD: '#b54708',
}

const SECTION_LABEL_STYLE = {
  fontFamily: 'var(--font-mono)',
  fontSize: '11px',
  letterSpacing: '0.1em',
  color: '#5f6c83',
  textTransform: 'uppercase' as const,
}

const PAGE_BREAK_AVOID = {
  breakInside: 'avoid' as const,
  pageBreakInside: 'avoid' as const,
}

export default function ChiefAnalystCard({ report, status, ticker, date, reports, chiefRawReport }: Props) {
  const [pdfError, setPdfError] = useState(false)
  const { toPDF, targetRef } = usePDF({
    filename: `${ticker}-${date}-chief-analyst-report.pdf`,
    page: {
      margin: { top: 10, right: 16, bottom: 10, left: 16 },
    },
  })
  const vm = report ? deriveChiefReportViewModel(report, reports, chiefRawReport) : null

  const handleDownload = () => {
    setPdfError(false)
    try { toPDF() } catch { setPdfError(true) }
  }

  return (
    <div
      data-testid="chief-analyst-card"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: '14px',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-4"
        style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}
      >
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.12em',
            color: 'var(--accent)',
            textTransform: 'uppercase',
          }}
        >
          Chief Analyst — Institutional Brief
        </div>

        {status === 'done' && report && (
          <div className="flex items-center gap-3">
            {pdfError && (
              <span style={{ fontSize: '11px', color: '#b42318', fontFamily: 'var(--font-mono)' }}>
                PDF failed — try again
              </span>
            )}
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all duration-150"
              style={{
                background: 'var(--accent-glow)',
                color: 'var(--accent-light)',
                border: '1px solid var(--accent-dim)',
                fontFamily: 'var(--font-mono)',
                letterSpacing: '0.06em',
                cursor: 'pointer',
              }}
            >
              ↓ Download PDF
            </button>
          </div>
        )}
      </div>

      {/* Body */}
      {status === 'pending' && (
        <div
          className="px-6 py-8 flex items-center gap-3"
          style={{ color: '#5f6c83', fontFamily: 'var(--font-mono)', fontSize: '12px', letterSpacing: '0.04em' }}
        >
          <div
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: '#99a4b8' }}
          />
          Chief Analyst is standing by…
        </div>
      )}

      {status === 'running' && (
        <div className="px-6 py-6 space-y-3">
          {[40, 70, 55, 80].map((w, i) => (
            <div
              key={i}
              className="h-3 rounded-full"
              style={{
                width: `${w}%`,
                background: '#dde5f1',
                animation: 'shimmer 1.2s ease-in-out infinite',
                animationDelay: `${i * 0.15}s`,
              }}
            />
          ))}
        </div>
      )}

      {status === 'done' && !report && (
        <div
          className="px-6 py-8"
          style={{ color: '#5f6c83', fontFamily: 'var(--font-mono)', fontSize: '12px' }}
        >
          Report unavailable for this run.
        </div>
      )}

      {status === 'done' && report && vm && (
        <div
          ref={targetRef}
          className="px-6 py-5 space-y-6"
          style={{ background: '#fdfefe', color: '#243042' }}
        >
          <div
            className="flex items-center justify-between"
            style={{ ...PAGE_BREAK_AVOID, border: '1px solid #e2e8f3', borderRadius: '10px', background: '#f7f9fd', padding: '8px 12px' }}
          >
            <span style={{ ...SECTION_LABEL_STYLE, fontSize: '10px', color: '#4b607d' }}>Ticker · {ticker || 'N/A'}</span>
            <span style={{ ...SECTION_LABEL_STYLE, fontSize: '10px', color: '#4b607d' }}>As Of · {date || 'N/A'}</span>
          </div>

          {/* Verdict + Time Horizon */}
          <div className="grid grid-cols-1 md:grid-cols-[auto,1fr] gap-6 items-start" style={PAGE_BREAK_AVOID}>
            <div className="flex flex-col gap-2">
              <div style={SECTION_LABEL_STYLE}>Verdict</div>
              <div
                className="px-5 py-2 rounded-lg font-bold w-fit"
                style={{
                  fontFamily: 'var(--font-syne)',
                  fontSize: '28px',
                  letterSpacing: '-0.02em',
                  color: VERDICT_COLOR[report.verdict] ?? '#243042',
                  border: `1px solid ${VERDICT_COLOR[report.verdict] ?? '#243042'}40`,
                  background: '#ffffff',
                }}
              >
                {report.verdict}
              </div>
            </div>

            <div>
              <div style={SECTION_LABEL_STYLE}>Time Horizon</div>
              <div className="mt-1.5">
                <p style={{ fontFamily: 'var(--font-syne)', fontSize: '24px', color: '#1f2f44', letterSpacing: '-0.01em' }}>
                  {vm.timeHorizon}
                </p>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#5f6c83', marginTop: '4px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  Confidence: {vm.timeHorizonConfidence}
                </p>
              </div>
            </div>
          </div>

          <section style={PAGE_BREAK_AVOID}>
            <div style={SECTION_LABEL_STYLE}>Catalyst Thesis</div>
            <p style={{ fontFamily: 'var(--font-manrope)', fontSize: '15px', color: '#2b3648', lineHeight: 1.72, marginTop: '6px' }}>
              {report.catalyst}
            </p>
          </section>

          <div style={{ height: '1px', background: '#dde5f1' }} />

          {/* Scenario Matrix */}
          <section style={PAGE_BREAK_AVOID}>
            <div style={SECTION_LABEL_STYLE}>Scenario Matrix</div>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-left" style={{ borderCollapse: 'collapse', tableLayout: 'fixed' }}>
                <colgroup>
                  <col style={{ width: '16%' }} />
                  <col style={{ width: '42%' }} />
                  <col style={{ width: '42%' }} />
                </colgroup>
                <thead>
                  <tr style={{ borderBottom: '1px solid #d5dbe7' }}>
                    <th style={{ ...SECTION_LABEL_STYLE, fontSize: '10px', padding: '8px 6px', color: '#445269' }}>Scenario</th>
                    <th style={{ ...SECTION_LABEL_STYLE, fontSize: '10px', padding: '8px 6px', color: '#445269' }}>Thesis</th>
                    <th style={{ ...SECTION_LABEL_STYLE, fontSize: '10px', padding: '8px 6px', color: '#445269' }}>Trigger / Condition</th>
                  </tr>
                </thead>
                <tbody>
                  {vm.scenarioMatrix.map((row) => (
                    <tr key={row.name} style={{ borderBottom: '1px solid #e7ecf4' }}>
                      <td style={{ padding: '10px 6px', fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#324661', letterSpacing: '0.04em' }}>
                        {row.name.toUpperCase()}
                      </td>
                      <td style={{ padding: '10px 6px', fontFamily: 'var(--font-manrope)', fontSize: '14px', color: '#2b3648', lineHeight: 1.6 }}>
                        {row.thesis}
                      </td>
                      <td style={{ padding: '10px 6px', fontFamily: 'var(--font-manrope)', fontSize: '14px', color: '#2b3648', lineHeight: 1.6 }}>
                        {row.trigger}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div style={{ height: '1px', background: '#dde5f1' }} />

          <div
            className="inline-flex items-center rounded-full px-2.5 py-1"
            style={{
              ...SECTION_LABEL_STYLE,
              fontSize: '9px',
              color: '#4a5e7a',
              background: '#f1f5fb',
              border: '1px solid #d7e0ee',
            }}
          >
            Page 2 · Detailed Notes
          </div>

          {/* Execution and Risk notes */}
          <section
            className="grid grid-cols-1 md:grid-cols-2 gap-6"
            style={{ breakBefore: 'page', pageBreakBefore: 'always', ...PAGE_BREAK_AVOID }}
          >
            <div>
              <div style={SECTION_LABEL_STYLE}>Execution Notes</div>
              <p style={{ fontFamily: 'var(--font-manrope)', fontSize: '14px', color: '#2b3648', lineHeight: 1.7, marginTop: '6px' }}>
                {report.execution}
              </p>
            </div>
            <div>
              <div style={SECTION_LABEL_STYLE}>Risk Notes</div>
              <p style={{ fontFamily: 'var(--font-manrope)', fontSize: '14px', color: '#2b3648', lineHeight: 1.7, marginTop: '6px' }}>
                {report.tail_risk}
              </p>
            </div>
          </section>

          <div style={{ height: '1px', background: '#dde5f1' }} />

          {/* Sources summary */}
          <footer
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              color: '#607089',
              letterSpacing: '0.04em',
              lineHeight: 1.6,
              breakInside: 'avoid',
              pageBreakInside: 'avoid',
            }}
          >
            {vm.sourcesSummary}
          </footer>
        </div>
      )}
    </div>
  )
}
