from __future__ import annotations
from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field


class BacktestMetricsPayload(BaseModel):
    initial_cash: float
    final_equity: float
    # None when initial_cash is 0 (division undefined); otherwise percent vs initial cash.
    total_return_pct: Optional[float] = None
    unrealized_pnl: float
    realized_pnl: float
    total_fees_paid: float
    fill_count: int
    max_drawdown_pct: Optional[float]  # None if not computed
    as_of: Optional[str]               # ISO datetime string, from metrics.as_of
    positions: dict[str, str]          # symbol → qty as string (Decimal-safe)
    terminal_exposure: Literal["long", "flat_closed", "flat_untraded"] = Field(
        description="End-of-run position state (backtest). Not an intraday trade signal.",
    )


def format_backtest_headline(
    ticker: str,
    start: date,
    end: date,
    payload: BacktestMetricsPayload,
) -> str:
    """Single-line scan summary derived only from ticker, date range, and metrics payload."""
    sym = ticker.strip().upper()
    if start == end:
        rng = start.isoformat()
    else:
        rng = f"{start.isoformat()} → {end.isoformat()}"
    ret = (
        f"{payload.total_return_pct:+.2f}%"
        if payload.total_return_pct is not None
        else "N/A%"
    )
    eq = f"${payload.final_equity:,.2f}"
    return f"{sym} · {rng} · {payload.fill_count} fills · Final {eq} · {ret}"
