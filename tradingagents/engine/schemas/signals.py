# tradingagents/engine/schemas/signals.py
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Annotated
from pydantic import Field
from tradingagents.engine.schemas.base import BaseSchema


class SignalDirection(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Signal(BaseSchema):
    symbol: str
    direction: SignalDirection
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    # float, NOT Decimal — model belief score, not a monetary quantity.
    # Bounds enforced via Pydantic Field constraints.
    reasoning: str
    generated_at: datetime           # UTC
    source_bar_timestamp: datetime   # bar T — fill will use T+1 open
