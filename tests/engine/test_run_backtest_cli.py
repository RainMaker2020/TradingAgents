"""Tests for run_backtest strategy lifecycle management."""
from __future__ import annotations

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
