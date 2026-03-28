# tests/engine/test_strategies.py
"""Unit tests for ``entry_signal`` / ``exit_signal`` helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from tradingagents.engine.schemas.market import Bar, MarketState
from tradingagents.engine.schemas.orders import RejectionCode
from tradingagents.engine.schemas.signals import SignalDirection
from tradingagents.engine.strategies.core import entry_signal, exit_signal
from tradingagents.engine.strategies.types import PositionSnapshot, StrategyParams

UTC = timezone.utc


def _bar(ts_day: int, close: str) -> Bar:
    ts = datetime(2026, 1, ts_day, tzinfo=UTC)
    o = Decimal("100")
    c = Decimal(close)
    return Bar(
        symbol="AAPL",
        timestamp=ts,
        open=o,
        high=c + Decimal("1"),
        low=c - Decimal("1"),
        close=c,
        volume=Decimal("1"),
    )


def _window(bars: list[Bar]) -> MarketState:
    last = bars[-1]
    return MarketState(
        symbol="AAPL",
        as_of=last.timestamp,
        latest_bar=last,
        bars_window=tuple(bars),
    )


class TestEntrySignal:
    def test_rejects_short_window(self):
        bars = [_bar(2, "100")]
        ms = _window(bars)
        r = entry_signal(ms, StrategyParams(short_window=5, long_window=20))
        assert r.code == RejectionCode.INSUFFICIENT_CONTEXT

    def test_buy_when_short_above_long(self):
        # Rising closes → short MA > long MA on last bar
        bars = [_bar(i, str(100 + i)) for i in range(2, 22)]
        ms = _window(bars)
        d, msg = entry_signal(ms, StrategyParams(short_window=5, long_window=20))
        assert d == SignalDirection.BUY
        assert "short_ma" in msg

    def test_hold_when_short_below_long(self):
        high_then_flat = [Decimal("150")] * 15 + [Decimal("100")] * 5
        bars = [
            _bar(i + 2, str(high_then_flat[i]))
            for i in range(20)
        ]
        ms = _window(bars)
        d, _msg = entry_signal(ms, StrategyParams(short_window=5, long_window=20))
        assert d == SignalDirection.HOLD


class TestExitSignal:
    def test_long_only_always_hold(self):
        bars = [_bar(i, str(100 + i)) for i in range(2, 22)]
        ms = _window(bars)
        pos = PositionSnapshot("AAPL", Decimal("10"), Decimal("100"))
        d, msg = exit_signal(ms, pos, StrategyParams(), long_only=True)
        assert d == SignalDirection.HOLD
        assert "long_only" in msg

    def test_sell_on_bearish_cross_when_not_long_only(self):
        # First 15 bars high, last 5 crash → short < long
        vals = [Decimal("200")] * 15 + [Decimal("90")] * 5
        bars = [_bar(i + 2, str(vals[i])) for i in range(20)]
        ms = _window(bars)
        pos = PositionSnapshot("AAPL", Decimal("10"), Decimal("150"))
        d, _msg = exit_signal(ms, pos, StrategyParams(), long_only=False)
        assert d == SignalDirection.SELL

    def test_flat_position_hold(self):
        bars = [_bar(i, str(100 + i)) for i in range(2, 22)]
        ms = _window(bars)
        pos = PositionSnapshot("AAPL", Decimal("0"), Decimal("0"))
        d, _msg = exit_signal(ms, pos, StrategyParams(), long_only=False)
        assert d == SignalDirection.HOLD
