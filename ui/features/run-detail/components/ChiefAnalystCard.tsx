'use client'
import { useState } from 'react'
import { usePDF } from 'react-to-pdf'
import type { ChiefAnalystReport } from '@/lib/types/agents'
import type { StepStatus } from '@/lib/types/agents'
import type { AgentStep } from '@/lib/types/run'
import { deriveChiefReportViewModel } from './chiefReportDerivation'
import ChiefAnalystPdfReport from './ChiefAnalystPdfReport'

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
        <>
          <div
            className="px-6 py-5 space-y-5"
            data-testid="chief-analyst-main"
            style={{ color: 'var(--text-primary)' }}
          >
            <div
              className="grid grid-cols-1 md:grid-cols-[auto,1fr] gap-4 items-start"
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                padding: '12px 14px',
              }}
            >
              <div className="space-y-2">
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Verdict
                </div>
                <div
                  className="px-4 py-1.5 rounded-lg font-bold w-fit"
                  style={{
                    fontFamily: 'var(--font-syne)',
                    fontSize: '24px',
                    color: VERDICT_COLOR[report.verdict] ?? 'var(--text-primary)',
                    border: `1px solid ${VERDICT_COLOR[report.verdict] ?? '#8da2c0'}70`,
                    background: `${VERDICT_COLOR[report.verdict] ?? '#8da2c0'}1A`,
                  }}
                >
                  {report.verdict}
                </div>
              </div>
              <div className="space-y-2">
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Time Horizon
                </div>
                <p style={{ fontFamily: 'var(--font-syne)', fontSize: '22px', color: 'var(--text-primary)', lineHeight: 1.2 }}>
                  {vm.timeHorizon}
                </p>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.09em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Confidence: {vm.timeHorizonConfidence}
                </p>
              </div>
            </div>

            <section>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Catalyst Thesis
              </div>
              <p style={{ fontFamily: 'var(--font-manrope)', fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.65, marginTop: '6px' }}>
                {report.catalyst}
              </p>
            </section>

            <section>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Scenario Matrix
              </div>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full text-left" style={{ borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      <th style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', color: 'var(--text-muted)', textTransform: 'uppercase', padding: '8px 6px' }}>Scenario</th>
                      <th style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', color: 'var(--text-muted)', textTransform: 'uppercase', padding: '8px 6px' }}>Thesis</th>
                      <th style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', color: 'var(--text-muted)', textTransform: 'uppercase', padding: '8px 6px' }}>Trigger / Condition</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vm.scenarioMatrix.map((row) => (
                      <tr key={row.name} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '8px 6px', fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-primary)' }}>{row.name.toUpperCase()}</td>
                        <td style={{ padding: '8px 6px', fontFamily: 'var(--font-manrope)', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.55 }}>{row.thesis}</td>
                        <td style={{ padding: '8px 6px', fontFamily: 'var(--font-manrope)', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.55 }}>{row.trigger}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Execution Notes
                </div>
                <p style={{ fontFamily: 'var(--font-manrope)', fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.65, marginTop: '6px' }}>
                  {report.execution}
                </p>
              </div>
              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Risk Notes
                </div>
                <p style={{ fontFamily: 'var(--font-manrope)', fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.65, marginTop: '6px' }}>
                  {report.tail_risk}
                </p>
              </div>
            </section>

            <footer
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                color: 'var(--text-muted)',
                letterSpacing: '0.04em',
                lineHeight: 1.6,
                borderTop: '1px solid var(--border)',
                paddingTop: '10px',
              }}
            >
              {vm.sourcesSummary}
            </footer>
          </div>

          <div
            aria-hidden
            style={{ position: 'fixed', left: '-10000px', top: 0, width: '1024px', zIndex: -1 }}
          >
            <ChiefAnalystPdfReport
              report={report}
              vm={vm}
              ticker={ticker}
              date={date}
              reportRef={targetRef}
            />
          </div>
        </>
      )}
    </div>
  )
}
