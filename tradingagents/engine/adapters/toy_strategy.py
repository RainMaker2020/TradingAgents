# tradingagents/engine/adapters/toy_strategy.py
"""Simple Moving Average Crossover strategy for backtest smoke-testing."""
from __future__ import annotations
from typing import Union

from tradingagents.engine.schemas.market import MarketState
from tradingagents.engine.schemas.orders import RejectionCode, RejectionReason
from tradingagents.engine.schemas.signals import Signal, SignalDirection


class MovingAverageCrossStrategy:
    """Emits BUY when the short MA is above the long MA, HOLD otherwise.

    Long-only by default: never emits SELL, so the portfolio cannot go short.
    Set long_only=False to emit SELL on bearish crossings.

    Satisfies the StrategyAgent Protocol.

    Args:
        short_window: Bars for the fast MA (default 5).
        long_window: Bars for the slow MA (default 20).
        confidence: Fixed confidence for all emitted signals (default 0.8).
        long_only: If True, emit HOLD instead of SELL on bearish crossings.
    """

    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 20,
        confidence: float = 0.8,
        long_only: bool = True,
    ) -> None:
        self._short = short_window
        self._long = long_window
        self._confidence = confidence
        self._long_only = long_only

    def generate_signal(
        self, market_state: MarketState
    ) -> Union[Signal, RejectionReason]:
        bars = market_state.bars_window
        if len(bars) < self._long:
            return RejectionReason(
                code=RejectionCode.INSUFFICIENT_CONTEXT,
                detail=f"need {self._long} bars, have {len(bars)}",
            )

        closes = [float(b.close) for b in bars]
        short_ma = sum(closes[-self._short:]) / self._short
        long_ma = sum(closes[-self._long:]) / self._long

        if short_ma > long_ma:
            direction = SignalDirection.BUY
        elif self._long_only:
            direction = SignalDirection.HOLD
        else:
            direction = SignalDirection.SELL

        return Signal(
            symbol=market_state.symbol,
            direction=direction,
            confidence=self._confidence,
            reasoning=(
                f"short_ma({self._short})={short_ma:.4f} "
                f"{'>' if short_ma > long_ma else '<='} "
                f"long_ma({self._long})={long_ma:.4f}"
            ),
            generated_at=market_state.as_of,
            source_bar_timestamp=market_state.latest_bar.timestamp,
        )
