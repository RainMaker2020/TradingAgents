import type { BacktestTraceEvent } from '@/lib/types/run'

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null && !Array.isArray(x)
}

/** Coerce API JSON into a safe list for the trace panel. */
export function normalizeBacktestTrace(raw: unknown): BacktestTraceEvent[] {
  if (!Array.isArray(raw)) return []
  const out: BacktestTraceEvent[] = []
  for (const row of raw) {
    if (!isRecord(row)) continue
    let rejection: BacktestTraceEvent['rejection'] = null
    const rejectionRaw = row.rejection
    if (rejectionRaw === null || rejectionRaw === undefined) {
      rejection = null
    } else if (isRecord(rejectionRaw)) {
      rejection = {
        code: typeof rejectionRaw.code === 'string' ? rejectionRaw.code : undefined,
        detail: typeof rejectionRaw.detail === 'string' ? rejectionRaw.detail : undefined,
      }
    }
    out.push({
      event_type: typeof row.event_type === 'string' ? row.event_type : undefined,
      timestamp: typeof row.timestamp === 'string' ? row.timestamp : undefined,
      symbol: typeof row.symbol === 'string' ? row.symbol : undefined,
      detail: typeof row.detail === 'string' ? row.detail : row.detail === null ? null : undefined,
      signal: isRecord(row.signal) ? row.signal : row.signal === null ? null : undefined,
      fill: isRecord(row.fill) ? row.fill : row.fill === null ? null : undefined,
      order: isRecord(row.order) ? row.order : row.order === null ? null : undefined,
      rejection,
    })
  }
  return out
}

function str(x: unknown): string {
  if (x === null || x === undefined) return ''
  return String(x)
}

const RISK_FORCED_PREFIX = 'risk_forced_exit:'

function riskForcedExitLabel(detail: string): string {
  if (detail === `${RISK_FORCED_PREFIX}stop_loss`) return 'Stop-loss (engine)'
  if (detail === `${RISK_FORCED_PREFIX}take_profit`) return 'Take-profit (engine)'
  return 'Risk exit (engine)'
}

/** One-line summary for the simulation timeline table. */
export function summarizeBacktestEvent(ev: BacktestTraceEvent): string {
  const rej = ev.rejection
  if (rej?.code || rej?.detail) {
    return [rej.code, rej.detail].filter(Boolean).join(' — ')
  }
  if (typeof ev.detail === 'string' && ev.detail.startsWith(RISK_FORCED_PREFIX)) {
    const sig = ev.signal
    const dir = sig && typeof sig.direction === 'string' ? sig.direction : 'SELL'
    const r = sig && typeof sig.reasoning === 'string' ? sig.reasoning : ''
    const clip = r.length > 100 ? `${r.slice(0, 97)}…` : r
    const head = riskForcedExitLabel(ev.detail)
    return clip ? `${head} · ${dir}: ${clip}` : `${head} · ${dir}`
  }
  const sig = ev.signal
  if (sig && typeof sig.direction === 'string') {
    const r = typeof sig.reasoning === 'string' ? sig.reasoning : ''
    const clip = r.length > 120 ? `${r.slice(0, 117)}…` : r
    return clip ? `${sig.direction}: ${clip}` : sig.direction
  }
  const fill = ev.fill
  if (fill) {
    const dir = str(fill.direction)
    const qty = str(fill.filled_quantity ?? fill.approved_quantity)
    const px = str(fill.fill_price)
    const fees = str(fill.fees)
    const parts = [`${dir} ${qty} @ ${px}`]
    if (fees) parts.push(`fees ${fees}`)
    return parts.join(' · ')
  }
  if (ev.event_type === 'DATA_SKIPPED') return 'No bar (weekend / holiday / missing row)'
  if (ev.event_type === 'SIGNAL_GENERATED') return 'Signal recorded (HOLD or pipeline)'
  if (ev.event_type === 'ORDER_APPROVED') return 'Order approved (see raw JSON for size)'
  return '—'
}

export function traceRowTone(
  ev: BacktestTraceEvent,
): 'buy' | 'sell' | 'hold' | 'warn' | 'muted' {
  if (
    ev.event_type === 'SIGNAL_GENERATED' &&
    typeof ev.detail === 'string' &&
    ev.detail.startsWith(RISK_FORCED_PREFIX)
  ) {
    return 'sell'
  }
  if (ev.event_type === 'FILL_EXECUTED' && ev.fill) {
    const d = str(ev.fill.direction).toUpperCase()
    if (d.includes('SELL')) return 'sell'
    if (d.includes('BUY')) return 'buy'
  }
  switch (ev.event_type) {
    case 'ORDER_REJECTED':
    case 'SIGNAL_REJECTED':
      return 'sell'
    case 'SIGNAL_GENERATED':
    case 'ORDER_APPROVED':
      return 'hold'
    case 'DATA_SKIPPED':
      return 'muted'
    case 'FILL_EXECUTED':
      return 'buy'
    default:
      return 'warn'
  }
}
