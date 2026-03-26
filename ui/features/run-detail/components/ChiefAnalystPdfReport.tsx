import type { RefObject } from 'react'
import type { ChiefAnalystReport } from '@/lib/types/agents'
import type { ChiefReportViewModel } from './chiefReportDerivation'

type Props = {
  report: ChiefAnalystReport
  vm: ChiefReportViewModel
  ticker: string
  date: string
  reportRef: RefObject<HTMLDivElement | null>
}

const VERDICT_COLOR: Record<string, string> = {
  BUY: '#087f5b',
  SELL: '#b42318',
  HOLD: '#b54708',
}

const SECTION_LABEL_STYLE = {
  fontFamily: 'var(--font-mono)',
  fontSize: '11px',
  letterSpacing: '0.12em',
  color: '#4f5f79',
  fontWeight: 700,
  textTransform: 'uppercase' as const,
}

const PAGE_BREAK_AVOID = {
  breakInside: 'avoid' as const,
  pageBreakInside: 'avoid' as const,
}

export default function ChiefAnalystPdfReport({ report, vm, ticker, date, reportRef }: Props) {
  return (
    <div
      ref={reportRef}
      className="px-6 py-5 space-y-7"
      style={{
        background: '#ffffff',
        color: '#1f2a3d',
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale',
        textRendering: 'geometricPrecision',
      }}
    >
      <div
        className="flex items-center justify-between"
        style={{
          ...PAGE_BREAK_AVOID,
          border: '1px solid #dde4f0',
          borderRadius: '12px',
          padding: '9px 13px',
        }}
      >
        <span style={{ ...SECTION_LABEL_STYLE, fontSize: '11px', color: '#4b607d' }}>Ticker · {ticker || 'N/A'}</span>
        <span style={{ ...SECTION_LABEL_STYLE, fontSize: '11px', color: '#4b607d' }}>As Of · {date || 'N/A'}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[auto,1fr] gap-6 items-start" style={{ ...PAGE_BREAK_AVOID, alignItems: 'stretch' }}>
        <div
          className="flex flex-col gap-3"
          style={{
            border: '1px solid #d7e0ee',
            borderRadius: '14px',
            padding: '14px',
          }}
        >
          <div style={SECTION_LABEL_STYLE}>Verdict</div>
          <div
            className="px-4 py-1.5 rounded-lg font-bold w-fit"
            style={{
              fontFamily: 'var(--font-syne)',
              fontSize: '28px',
              letterSpacing: '-0.02em',
              color: VERDICT_COLOR[report.verdict] ?? '#243042',
              border: `1px solid ${VERDICT_COLOR[report.verdict] ?? '#243042'}70`,
              background: `${VERDICT_COLOR[report.verdict] ?? '#243042'}1A`,
            }}
          >
            {report.verdict}
          </div>
          <p
            style={{
              fontFamily: 'var(--font-manrope)',
              fontSize: '15px',
              color: '#53637a',
              lineHeight: 1.55,
              maxWidth: '28ch',
            }}
          >
            Institutional stance synthesized across market, sentiment, news, and risk controls.
          </p>
        </div>

        <div
          style={{
            border: '1px solid #d7e0ee',
            borderRadius: '14px',
            padding: '14px 16px',
          }}
        >
          <div style={SECTION_LABEL_STYLE}>Time Horizon</div>
          <div className="mt-2">
            <p style={{ fontFamily: 'var(--font-syne)', fontSize: '32px', color: '#1f2f44', letterSpacing: '-0.015em', lineHeight: 1.15 }}>
              {vm.timeHorizon}
            </p>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#5f6c83', marginTop: '10px', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
              Confidence: {vm.timeHorizonConfidence}
            </p>
          </div>
        </div>
      </div>

      <section
        style={{
          ...PAGE_BREAK_AVOID,
          border: '1px solid #d7e0ee',
          borderRadius: '14px',
          padding: '14px 16px',
        }}
      >
        <div style={SECTION_LABEL_STYLE}>Catalyst Thesis</div>
        <p style={{ fontFamily: 'var(--font-manrope)', fontSize: '16px', color: '#2b3648', lineHeight: 1.74, marginTop: '8px' }}>
          {report.catalyst}
        </p>
      </section>

      <div style={{ height: '1px', background: '#d8e0ec' }} />

      <section
        style={{
          ...PAGE_BREAK_AVOID,
          border: '1px solid #d7e0ee',
          borderRadius: '14px',
          padding: '14px 16px',
        }}
      >
        <div style={SECTION_LABEL_STYLE}>Scenario Matrix</div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left" style={{ borderCollapse: 'collapse', tableLayout: 'fixed' }}>
            <colgroup>
              <col style={{ width: '18%' }} />
              <col style={{ width: '41%' }} />
              <col style={{ width: '41%' }} />
            </colgroup>
            <thead>
              <tr style={{ borderBottom: '1px solid #d5dbe7' }}>
                <th style={{ ...SECTION_LABEL_STYLE, fontSize: '11px', padding: '9px 8px', color: '#445269' }}>Scenario</th>
                <th style={{ ...SECTION_LABEL_STYLE, fontSize: '11px', padding: '9px 8px', color: '#445269' }}>Thesis</th>
                <th style={{ ...SECTION_LABEL_STYLE, fontSize: '11px', padding: '9px 8px', color: '#445269' }}>Trigger / Condition</th>
              </tr>
            </thead>
            <tbody>
              {vm.scenarioMatrix.map((row) => (
                <tr key={row.name} style={{ borderBottom: '1px solid #e7ecf4' }}>
                  <td style={{ padding: '11px 8px', fontFamily: 'var(--font-mono)', fontSize: '13px', color: '#324661', letterSpacing: '0.08em' }}>
                    {row.name.toUpperCase()}
                  </td>
                  <td style={{ padding: '11px 8px', fontFamily: 'var(--font-manrope)', fontSize: '15px', color: '#2b3648', lineHeight: 1.62 }}>
                    {row.thesis}
                  </td>
                  <td style={{ padding: '11px 8px', fontFamily: 'var(--font-manrope)', fontSize: '15px', color: '#2b3648', lineHeight: 1.62 }}>
                    {row.trigger}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div style={{ height: '1px', background: '#d8e0ec' }} />

      <div
        className="inline-flex items-center rounded-full px-2.5 py-1"
        style={{
          ...SECTION_LABEL_STYLE,
          fontSize: '10px',
          color: '#4a5e7a',
          border: '1px solid #d7e0ee',
        }}
      >
        Page 2 · Detailed Notes
      </div>

      <section
        className="grid grid-cols-1 md:grid-cols-2 gap-6"
        style={{ breakBefore: 'page', pageBreakBefore: 'always', ...PAGE_BREAK_AVOID }}
      >
        <div
          style={{
            border: '1px solid #d7e0ee',
            borderRadius: '14px',
            padding: '14px 16px',
          }}
        >
          <div style={SECTION_LABEL_STYLE}>Execution Notes</div>
          <p style={{ fontFamily: 'var(--font-manrope)', fontSize: '15px', color: '#2b3648', lineHeight: 1.7, marginTop: '8px' }}>
            {report.execution}
          </p>
        </div>
        <div
          style={{
            border: '1px solid #d7e0ee',
            borderRadius: '14px',
            padding: '14px 16px',
          }}
        >
          <div style={SECTION_LABEL_STYLE}>Risk Notes</div>
          <p style={{ fontFamily: 'var(--font-manrope)', fontSize: '15px', color: '#2b3648', lineHeight: 1.7, marginTop: '8px' }}>
            {report.tail_risk}
          </p>
        </div>
      </section>

      <div style={{ height: '1px', background: '#d8e0ec' }} />

      <footer
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
          color: '#607089',
          letterSpacing: '0.04em',
          lineHeight: 1.6,
          border: '1px solid #d7e0ee',
          borderRadius: '12px',
          padding: '10px 12px',
          breakInside: 'avoid',
          pageBreakInside: 'avoid',
        }}
      >
        {vm.sourcesSummary}
      </footer>
    </div>
  )
}
