# tradingagents/engine/schemas/market.py
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Literal
from tradingagents.engine.schemas.base import BaseSchema


class Bar(BaseSchema):
    symbol: str
    timestamp: datetime          # UTC, enforced by BaseSchema
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal              # Decimal for future VWAP calculation
    vwap: Decimal | None = None


class Tick(BaseSchema):
    # Schema only — TickFeed Protocol is deferred to a future release.
    symbol: str
    timestamp: datetime          # UTC
    price: Decimal
    size: Decimal
    side: Literal["bid", "ask", "trade"]


class MarketState(BaseSchema):
    symbol: str
    as_of: datetime              # UTC; should equal latest_bar.timestamp
    latest_bar: Bar
    bars_window: tuple[Bar, ...] # tuple (not list) — safe with frozen=True
    # Constructed by BacktestLoop from a rolling window of Bar objects.
    # Most-recent bar is last.
