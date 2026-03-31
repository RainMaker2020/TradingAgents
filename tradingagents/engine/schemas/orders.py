# tradingagents/engine/schemas/orders.py
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID
from tradingagents.engine.schemas.base import BaseSchema
from tradingagents.engine.schemas.signals import SignalDirection


class FillModel(Enum):
    NEXT_OPEN = "NEXT_OPEN"    # v1 active: fill at next bar's open price
    SAME_CLOSE = "SAME_CLOSE"  # future
    VWAP = "VWAP"              # future


class Order(BaseSchema):
    id: UUID
    symbol: str
    direction: SignalDirection
    quantity: Decimal
    created_at: datetime               # UTC
    fill_model: FillModel = FillModel.NEXT_OPEN
    signal_ref: UUID | None = None     # traceability to originating Signal


class ApprovedOrder(BaseSchema):
    order: Order
    approved_at: datetime              # UTC
    approved_quantity: Decimal


class RejectionCode(Enum):
    # Feed-level
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    BAR_NOT_FOUND = "BAR_NOT_FOUND"
    # Execution-level
    NO_NEXT_BAR = "NO_NEXT_BAR"
    MARKET_CLOSED = "MARKET_CLOSED"
    # Risk-level
    INSUFFICIENT_CASH = "INSUFFICIENT_CASH"
    EXCEEDS_POSITION_LIMIT = "EXCEEDS_POSITION_LIMIT"
    RISK_THRESHOLD_BREACHED = "RISK_THRESHOLD_BREACHED"
    DRAWDOWN_LIMIT_BREACHED = "DRAWDOWN_LIMIT_BREACHED"
    # Strategy-level
    STRATEGY_TIMEOUT = "STRATEGY_TIMEOUT"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class RejectionReason(BaseSchema):
    code: RejectionCode
    detail: str | None = None


class FillResult(BaseSchema):
    order_id: UUID
    symbol: str
    direction: SignalDirection         # added vs spec: needed by Portfolio.apply_fill
    approved_quantity: Decimal
    filled_quantity: Decimal
    fill_price: Decimal                # T+1 open + slippage
    slippage: Decimal                  # in price units
    fees: Decimal                      # in cash units
    filled_at: datetime                # UTC; equals next_bar.timestamp

    @property
    def is_partial(self) -> bool:
        # v1: FillResult is only emitted on a full fill; is_partial is always False.
        # Defined here as an extension point for v2 partial-fill support.
        return self.filled_quantity < self.approved_quantity
