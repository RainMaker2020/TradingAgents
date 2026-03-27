# tradingagents/engine/contracts/portfolio.py
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from tradingagents.engine.schemas.orders import FillResult
from tradingagents.engine.schemas.portfolio import PortfolioMetrics, PortfolioState
from tradingagents.engine.schemas.config import SimulationConfig


class Portfolio(ABC):
    @abstractmethod
    def apply_fill(
        self,
        state: PortfolioState,
        fill: FillResult,
    ) -> PortfolioState:
        # Pure function. Input state is frozen; returns a NEW PortfolioState.
        # MUST NOT mutate input state.
        ...

    @abstractmethod
    def mark_to_market(
        self,
        state: PortfolioState,
        prices: dict[str, Decimal],
    ) -> PortfolioMetrics: ...

    @classmethod   # intentionally NOT @abstractmethod — default works for all v1 impls
    def initial_state(
        cls,
        config: SimulationConfig,
        as_of: datetime,            # supplied by orchestrator; no wall-clock time
    ) -> PortfolioState:
        """Factory for zero-position starting state.
        as_of MUST be the first bar's timestamp, set by BacktestLoop.
        Subclasses MAY override (e.g. to seed existing positions for paper trading),
        but are not required to.
        """
        return PortfolioState(
            as_of=as_of,
            cash=config.initial_cash,
            positions={},
            cost_basis={},
        )
