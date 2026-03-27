from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from tradingagents.engine.schemas.base import BaseSchema
from tradingagents.engine.schemas.orders import FillResult, RejectionReason


class PortfolioState(BaseSchema):
    as_of: datetime
    cash: Decimal
    positions: dict[str, Decimal]   # symbol → quantity; v1 long-only (qty >= 0)
    cost_basis: dict[str, Decimal]  # symbol → average entry price


class PortfolioMetrics(BaseSchema):
    as_of: datetime
    total_equity: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_fees_paid: Decimal
    max_drawdown_pct: Decimal
    sharpe_ratio: float | None = None


class BacktestEventType(Enum):
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    SIGNAL_REJECTED = "SIGNAL_REJECTED"   # strategy stage: no order yet exists
    ORDER_APPROVED = "ORDER_APPROVED"
    ORDER_REJECTED = "ORDER_REJECTED"     # risk or execution stage
    FILL_EXECUTED = "FILL_EXECUTED"
    DATA_SKIPPED = "DATA_SKIPPED"


class BacktestEvent(BaseSchema):
    event_type: BacktestEventType
    timestamp: datetime                        # UTC; bar timestamp of the event
    symbol: str
    detail: str | None = None
    fill: FillResult | None = None             # populated for FILL_EXECUTED
    rejection: RejectionReason | None = None   # populated for SIGNAL_REJECTED,
                                               # ORDER_REJECTED, DATA_SKIPPED


class BacktestResult(BaseSchema):
    symbol: str
    start: date
    end: date
    initial_state: PortfolioState
    final_state: PortfolioState
    events: tuple[BacktestEvent, ...]   # tuple for frozen-safe immutability
    metrics: PortfolioMetrics
