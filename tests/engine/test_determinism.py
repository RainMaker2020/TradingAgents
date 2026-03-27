# tests/engine/test_determinism.py
"""Determinism test: same inputs, same SimulationConfig(random_seed=42) → identical outputs.

Scope: engine/runtime/fakes only.
External feeds (yfinance, Alpha Vantage) are outside this guarantee.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from tradingagents.engine.runtime.backtest_loop import BacktestLoop
from tradingagents.engine.runtime.paper_portfolio import InMemoryPortfolio
from tradingagents.engine.runtime.simulator import ConcreteExecutionSimulator
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.signals import SignalDirection

from tests.engine.fakes import (
    FakeDataFeed, FakeRiskManager, FakeStrategyAgent,
    make_bar, make_signal,
)

UTC = timezone.utc
START = date(2026, 1, 2)
END = date(2026, 1, 9)
CFG = SimulationConfig(
    initial_cash=Decimal("100000"),
    slippage_bps=Decimal("5"),
    fee_per_trade=Decimal("1.0"),
    random_seed=42,
)


def _make_run():
    bars = [
        make_bar(ts=datetime(2026, 1, 2 + i, tzinfo=UTC), open=str(150 + i), close=str(151 + i))
        for i in range(6)
    ]
    signals = [make_signal(ts=b.timestamp) for b in bars]  # all BUY

    feed = FakeDataFeed(bars)
    strategy = FakeStrategyAgent(signals)
    risk = FakeRiskManager()
    simulator = ConcreteExecutionSimulator()
    portfolio = InMemoryPortfolio()

    return BacktestLoop(feed, strategy, risk, simulator, portfolio, CFG).run("AAPL", START, END)


class TestDeterminism:
    def test_two_runs_produce_identical_fill_prices(self):
        r1 = _make_run()
        r2 = _make_run()
        fills1 = [e.fill for e in r1.events if e.fill is not None]
        fills2 = [e.fill for e in r2.events if e.fill is not None]
        assert len(fills1) == len(fills2)
        for f1, f2 in zip(fills1, fills2):
            assert f1.fill_price == f2.fill_price, f"fill_price mismatch: {f1.fill_price} != {f2.fill_price}"
            assert f1.slippage == f2.slippage
            assert f1.fees == f2.fees

    def test_two_runs_produce_identical_final_state(self):
        r1 = _make_run()
        r2 = _make_run()
        assert r1.final_state == r2.final_state

    def test_two_runs_produce_identical_event_count(self):
        r1 = _make_run()
        r2 = _make_run()
        assert len(r1.events) == len(r2.events)

    def test_two_runs_produce_identical_events_tuple(self):
        r1 = _make_run()
        r2 = _make_run()
        assert r1.events == r2.events
