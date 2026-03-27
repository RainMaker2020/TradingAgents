# tradingagents/engine/contracts/risk.py
from __future__ import annotations
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Union
from tradingagents.engine.schemas.signals import Signal
from tradingagents.engine.schemas.orders import ApprovedOrder, RejectionReason
from tradingagents.engine.schemas.portfolio import PortfolioState
from tradingagents.engine.schemas.config import SimulationConfig


class RiskManager(ABC):
    @abstractmethod
    def evaluate(
        self,
        signal: Signal,
        portfolio: PortfolioState,
        current_prices: dict[str, Decimal],
        config: SimulationConfig,
    ) -> Union[ApprovedOrder, RejectionReason]: ...

    def compute_position_size(
        self,
        signal: Signal,
        portfolio: PortfolioState,
        current_prices: dict[str, Decimal],
        config: SimulationConfig,
    ) -> Decimal:
        """Default: confidence × max_position_pct × total mark-to-market equity → dollar notional.

        Returns dollar notional. Callers are responsible for dividing by price
        to get share count. current_prices supplied by the orchestrator; not fetched internally.
        Quantize to Decimal("0.01") (cents).
        """
        position_value = sum(
            qty * current_prices.get(sym, Decimal("0"))
            for sym, qty in portfolio.positions.items()
        )
        total_equity = portfolio.cash + position_value
        return (
            Decimal(str(signal.confidence))
            * config.max_position_pct
            * total_equity
        ).quantize(Decimal("0.01"))
