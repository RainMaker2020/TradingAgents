"""Pure entry/exit signal helpers for processing `MarketState` (no I/O, no LLM).

Concrete `StrategyAgent` adapters compose these functions to turn bar windows into
`Signal` objects. Risk limits (stop loss, drawdown caps, position size) are
enforced in `ConcreteRiskManager` and `BacktestLoop`, not here.

Moving averages use ``Decimal`` bar closes so crossover logic stays consistent
with the rest of the engine (no float conversion of prices).
"""
from __future__ import annotations

from decimal import Decimal

from tradingagents.engine.schemas.market import MarketState
from tradingagents.engine.schemas.orders import RejectionCode, RejectionReason
from tradingagents.engine.schemas.signals import SignalDirection
from tradingagents.engine.strategies.types import PositionSnapshot, StrategyParams


def _moving_averages(
    market_state: MarketState, params: StrategyParams
) -> tuple[Decimal, Decimal] | RejectionReason:
    bars = market_state.bars_window
    need = params.long_window
    if len(bars) < need:
        return RejectionReason(
            code=RejectionCode.INSUFFICIENT_CONTEXT,
            detail=f"need {need} bars, have {len(bars)}",
        )
    closes = [b.close for b in bars]
    sw = Decimal(params.short_window)
    lw = Decimal(params.long_window)
    short_ma = sum(closes[-params.short_window :], start=Decimal("0")) / sw
    long_ma = sum(closes[-params.long_window :], start=Decimal("0")) / lw
    return short_ma, long_ma


def entry_signal(
    market_state: MarketState,
    params: StrategyParams,
) -> tuple[SignalDirection, str] | RejectionReason:
    """Long-only entry rule: BUY when fast MA is above slow MA; else HOLD.

    Returns ``RejectionReason`` when the bar window is too short (same semantics
    as a strategy-stage rejection).
    """
    ma = _moving_averages(market_state, params)
    if isinstance(ma, RejectionReason):
        return ma
    short_ma, long_ma = ma
    if short_ma > long_ma:
        return (
            SignalDirection.BUY,
            (
                f"entry: short_ma({params.short_window})={short_ma:.4f} > "
                f"long_ma({params.long_window})={long_ma:.4f}"
            ),
        )
    return (
        SignalDirection.HOLD,
        (
            f"entry: short_ma({params.short_window})={short_ma:.4f} <= "
            f"long_ma({params.long_window})={long_ma:.4f}"
        ),
    )


def exit_signal(
    market_state: MarketState,
    position: PositionSnapshot,
    params: StrategyParams,
    *,
    long_only: bool = True,
) -> tuple[SignalDirection, str] | RejectionReason:
    """Exit rule for an existing long: SELL on bearish MA cross when ``long_only`` is False.

    When ``long_only`` is True (default), returns HOLD so exits are driven by
    risk overlays (stop / take-profit) or a separate policy.

    If ``position.quantity`` is not positive, returns HOLD without inspecting bars.
    """
    if position.quantity <= 0:
        return SignalDirection.HOLD, "exit: flat position"

    if long_only:
        return SignalDirection.HOLD, "exit: long_only (no discretionary exit)"

    ma = _moving_averages(market_state, params)
    if isinstance(ma, RejectionReason):
        return ma
    short_ma, long_ma = ma
    if short_ma < long_ma:
        return (
            SignalDirection.SELL,
            (
                f"exit: short_ma({params.short_window})={short_ma:.4f} < "
                f"long_ma({params.long_window})={long_ma:.4f}"
            ),
        )
    return (
        SignalDirection.HOLD,
        (
            f"exit: short_ma({params.short_window})={short_ma:.4f} >= "
            f"long_ma({params.long_window})={long_ma:.4f}"
        ),
    )
