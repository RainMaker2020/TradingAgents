"""Tests for run_backtest strategy lifecycle management."""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

import run_backtest


def _fake_result():
    return SimpleNamespace(
        events=[],
        metrics=SimpleNamespace(
            total_equity=Decimal("100000"),
            unrealized_pnl=Decimal("0"),
        ),
        final_state=SimpleNamespace(positions={}),
    )


def test_run_backtest_closes_strategy_on_success(monkeypatch):
    created = []

    class FakeStrategy:
        def __init__(self, *args, **kwargs):
            self.closed = False
            created.append(self)

        def close(self):
            self.closed = True

    class FakeBacktestLoop:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, symbol, start, end):
            return _fake_result()

    monkeypatch.setattr(run_backtest, "LangGraphStrategyAdapter", FakeStrategy)
    monkeypatch.setattr(run_backtest, "BacktestLoop", FakeBacktestLoop)
    monkeypatch.setattr(run_backtest, "CsvDataFeed", lambda symbol: object())
    monkeypatch.setattr(run_backtest, "ConcreteRiskManager", lambda: object())
    monkeypatch.setattr(run_backtest, "ConcreteExecutionSimulator", lambda: object())
    monkeypatch.setattr(run_backtest, "InMemoryPortfolio", lambda: object())

    run_backtest.run("AAPL", date(2024, 1, 2), date(2024, 1, 3), toy=False)

    assert len(created) == 1
    assert created[0].closed is True


def test_run_backtest_closes_strategy_on_backtest_error(monkeypatch):
    created = []

    class FakeStrategy:
        def __init__(self, *args, **kwargs):
            self.closed = False
            created.append(self)

        def close(self):
            self.closed = True

    class FailingBacktestLoop:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, symbol, start, end):
            raise RuntimeError("simulated failure")

    monkeypatch.setattr(run_backtest, "LangGraphStrategyAdapter", FakeStrategy)
    monkeypatch.setattr(run_backtest, "BacktestLoop", FailingBacktestLoop)
    monkeypatch.setattr(run_backtest, "CsvDataFeed", lambda symbol: object())
    monkeypatch.setattr(run_backtest, "ConcreteRiskManager", lambda: object())
    monkeypatch.setattr(run_backtest, "ConcreteExecutionSimulator", lambda: object())
    monkeypatch.setattr(run_backtest, "InMemoryPortfolio", lambda: object())

    with pytest.raises(RuntimeError, match="simulated failure"):
        run_backtest.run("AAPL", date(2024, 1, 2), date(2024, 1, 3), toy=False)

    assert len(created) == 1
    assert created[0].closed is True


def test_simulation_config_input_kwargs_normalizes_risk_percents():
    kw = run_backtest._simulation_config_input_kwargs(
        initial_cash=100_000,
        slippage_bps=5,
        fee_per_trade=1.0,
        max_position_pct=10,
        stop_loss_percentage=5.0,
        take_profit_target=12.5,
        max_drawdown_limit=15.0,
        max_position_size=500.0,
        min_confidence_threshold=0.7,
        fee_bps=3.0,
    )
    cfg = run_backtest.SimulationConfigInput(**kw).to_simulation_config()
    assert cfg.stop_loss_pct == Decimal("0.05")
    assert cfg.take_profit_pct == Decimal("0.125")
    assert cfg.max_drawdown_limit == Decimal("0.15")
    assert cfg.max_position_size == Decimal("500")
    assert cfg.min_confidence_threshold == 0.7
    assert cfg.fee_bps == Decimal("3")


def test_cli_rejects_end_before_start(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_backtest", "--start", "2024-01-10", "--end", "2024-01-01", "--toy"],
    )
    with pytest.raises(SystemExit):
        run_backtest.main()
