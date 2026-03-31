# tests/engine/test_backtest_loop.py
"""Tests for BacktestLoop helpers and risk-forced exit wiring."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from tradingagents.engine.runtime.backtest_loop import _stop_take_profit_signal
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.market import Bar
from tradingagents.engine.schemas.portfolio import PortfolioState
from tradingagents.engine.schemas.signals import SignalDirection

UTC = timezone.utc


def _bar(close: str) -> Bar:
    ts = datetime(2026, 1, 10, 21, 0, 0, tzinfo=UTC)
    c = Decimal(close)
    return Bar(
        symbol="AAPL",
        timestamp=ts,
        open=c,
        high=c + Decimal("1"),
        low=c - Decimal("1"),
        close=c,
        volume=Decimal("1"),
    )


def _portfolio(qty: str, entry: str) -> PortfolioState:
    ts = datetime(2026, 1, 9, 21, 0, 0, tzinfo=UTC)
    return PortfolioState(
        as_of=ts,
        cash=Decimal("0"),
        positions={"AAPL": Decimal(qty)},
        cost_basis={"AAPL": Decimal(entry)},
    )


def test_stop_take_signal_triggers_stop_loss():
    cfg = SimulationConfig(
        initial_cash=Decimal("100000"),
        stop_loss_pct=Decimal("0.05"),
    )
    bar = _bar("94")  # entry 100 → floor 95
    pair = _stop_take_profit_signal("AAPL", _portfolio("10", "100"), bar, cfg)
    assert pair is not None
    sig, kind = pair
    assert sig.direction == SignalDirection.SELL
    assert kind == "stop_loss"
    assert "stop_loss" in sig.reasoning


def test_stop_take_signal_no_trigger_when_above_floor():
    cfg = SimulationConfig(
        initial_cash=Decimal("100000"),
        stop_loss_pct=Decimal("0.05"),
    )
    bar = _bar("96")
    assert _stop_take_profit_signal("AAPL", _portfolio("10", "100"), bar, cfg) is None


def test_stop_take_signal_triggers_take_profit():
    cfg = SimulationConfig(
        initial_cash=Decimal("100000"),
        take_profit_pct=Decimal("0.10"),
    )
    bar = _bar("111")  # entry 100 → target 110
    pair = _stop_take_profit_signal("AAPL", _portfolio("10", "100"), bar, cfg)
    assert pair is not None
    sig, kind = pair
    assert sig.direction == SignalDirection.SELL
    assert kind == "take_profit"
    assert "take_profit" in sig.reasoning


def test_stop_take_signal_flat_portfolio():
    cfg = SimulationConfig(
        initial_cash=Decimal("100000"),
        stop_loss_pct=Decimal("0.05"),
    )
    state = PortfolioState(
        as_of=datetime(2026, 1, 9, 21, 0, 0, tzinfo=UTC),
        cash=Decimal("100000"),
        positions={},
        cost_basis={},
    )
    assert _stop_take_profit_signal("AAPL", state, _bar("90"), cfg) is None
