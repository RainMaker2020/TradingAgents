# tradingagents/engine/contracts/execution.py
from __future__ import annotations
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Union
from tradingagents.engine.schemas.market import Bar
from tradingagents.engine.schemas.orders import ApprovedOrder, FillResult, RejectionReason
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.contracts.feeds import MarketCalendar


class ExecutionSimulator(ABC):
    @abstractmethod
    def fill(
        self,
        order: ApprovedOrder,
        next_bar: Bar | None,
        calendar: MarketCalendar,
        config: SimulationConfig,
    ) -> Union[FillResult, RejectionReason]:
        # Fill evaluation precedence — ALL implementations MUST follow:
        # 1. next_bar is None           → RejectionReason(NO_NEXT_BAR)
        # 2. not calendar.is_trading_day(next_bar.timestamp.date())
        #                               → RejectionReason(MARKET_CLOSED)
        # 3. compute fill at next_bar.open + slippage + fees
        ...

    def _calculate_slippage(self, price: Decimal, config: SimulationConfig) -> Decimal:
        """slippage_bps applied symmetrically. Direction applied by fill()."""
        return (price * config.slippage_bps / Decimal("10000")).quantize(
            Decimal("0.0001")
        )

    def _calculate_fees(
        self, quantity: Decimal, price: Decimal, config: SimulationConfig
    ) -> Decimal:
        """Additive: flat fee_per_trade + optional fee_bps on notional."""
        flat = config.fee_per_trade
        bps_fee = (
            quantity * price * config.fee_bps / Decimal("10000")
            if config.fee_bps is not None
            else Decimal("0")
        )
        return flat + bps_fee
