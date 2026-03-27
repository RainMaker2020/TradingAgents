# tradingagents/engine/runtime/simulator.py
from __future__ import annotations
from decimal import Decimal
from typing import Union

from tradingagents.engine.contracts.execution import ExecutionSimulator
from tradingagents.engine.contracts.feeds import MarketCalendar
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.market import Bar
from tradingagents.engine.schemas.orders import (
    ApprovedOrder, FillResult, RejectionCode, RejectionReason,
)
from tradingagents.engine.schemas.signals import SignalDirection


class ConcreteExecutionSimulator(ExecutionSimulator):
    """v1 simulator: fills at next_bar.open with symmetric slippage + additive fees.

    Fill evaluation precedence:
    1. next_bar is None           → NO_NEXT_BAR
    2. market closed on T+1       → MARKET_CLOSED
    3. compute fill               → FillResult
    """

    def fill(
        self,
        order: ApprovedOrder,
        next_bar: Bar | None,
        calendar: MarketCalendar,
        config: SimulationConfig,
    ) -> Union[FillResult, RejectionReason]:
        # Precedence 1
        if next_bar is None:
            return RejectionReason(code=RejectionCode.NO_NEXT_BAR)
        # Precedence 2
        if not calendar.is_trading_day(next_bar.timestamp.date()):
            return RejectionReason(code=RejectionCode.MARKET_CLOSED)

        # Compute fill
        slippage = self._calculate_slippage(next_bar.open, config)
        fees = self._calculate_fees(order.approved_quantity, next_bar.open, config)

        if order.order.direction == SignalDirection.BUY:
            fill_price = next_bar.open + slippage
        else:
            fill_price = next_bar.open - slippage

        return FillResult(
            order_id=order.order.id,
            symbol=order.order.symbol,
            direction=order.order.direction,
            approved_quantity=order.approved_quantity,
            filled_quantity=order.approved_quantity,  # v1: full fill only
            fill_price=fill_price,
            slippage=slippage,
            fees=fees,
            filled_at=next_bar.timestamp,
        )
