# tradingagents/engine/adapters/toy_strategy.py
"""Simple Moving Average Crossover strategy for backtest smoke-testing."""
from __future__ import annotations
from decimal import Decimal
from typing import Union

from tradingagents.engine.schemas.market import MarketState
from tradingagents.engine.schemas.orders import RejectionReason
from tradingagents.engine.schemas.portfolio import PortfolioState
from tradingagents.engine.schemas.signals import Signal, SignalDirection
from tradingagents.engine.strategies.core import entry_signal, exit_signal
from tradingagents.engine.strategies.types import PositionSnapshot, StrategyParams


class MovingAverageCrossStrategy:
    """Emits BUY/HOLD from ``entry_signal``; optional SELL from ``exit_signal`` when not long-only.

    Composes the shared ``entry_signal`` / ``exit_signal`` helpers in
    ``tradingagents.engine.strategies`` so agents and tests use one rule
    implementation.

    Satisfies the StrategyAgent Protocol.

    Args:
        short_window: Bars for the fast MA (default 5).
        long_window: Bars for the slow MA (default 20).
        confidence: Fixed confidence for all emitted signals (default 0.8).
        long_only: If True, exit_signal stays HOLD; rely on risk overlays to flat.
    """

    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 20,
        confidence: float = 0.8,
        long_only: bool = True,
    ) -> None:
        self._params = StrategyParams(short_window=short_window, long_window=long_window)
        self._confidence = confidence
        self._long_only = long_only

    def generate_signal(
        self,
        market_state: MarketState,
        portfolio: PortfolioState | None = None,
    ) -> Union[Signal, RejectionReason]:
        sym = market_state.symbol
        qty = Decimal("0")
        avg_entry = Decimal("0")
        if portfolio is not None:
            qty = portfolio.positions.get(sym, Decimal("0"))
            avg_entry = portfolio.cost_basis.get(sym, Decimal("0"))

        if qty > Decimal("0"):
            pos = PositionSnapshot(symbol=sym, quantity=qty, avg_entry_price=avg_entry)
            ex = exit_signal(
                market_state, pos, self._params, long_only=self._long_only
            )
            if isinstance(ex, RejectionReason):
                return ex
            direction, reasoning = ex
            return Signal(
                symbol=sym,
                direction=direction,
                confidence=self._confidence,
                reasoning=reasoning,
                generated_at=market_state.as_of,
                source_bar_timestamp=market_state.latest_bar.timestamp,
            )

        en = entry_signal(market_state, self._params)
        if isinstance(en, RejectionReason):
            return en
        direction, reasoning = en
        return Signal(
            symbol=sym,
            direction=direction,
            confidence=self._confidence,
            reasoning=reasoning,
            generated_at=market_state.as_of,
            source_bar_timestamp=market_state.latest_bar.timestamp,
        )
