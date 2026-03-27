# tests/engine/test_smoke.py
"""End-to-end smoke test for BacktestLoop."""
from __future__ import annotations
import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from tradingagents.engine.runtime.backtest_loop import BacktestLoop
from tradingagents.engine.runtime.paper_portfolio import InMemoryPortfolio
from tradingagents.engine.runtime.simulator import ConcreteExecutionSimulator
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.orders import RejectionCode, RejectionReason
from tradingagents.engine.schemas.portfolio import BacktestEventType
from tradingagents.engine.schemas.signals import SignalDirection

from tests.engine.fakes import (
    FakeDataFeed, FakeRiskManager, FakeStrategyAgent,
    make_bar, make_signal,
)

UTC = timezone.utc
START = date(2026, 1, 2)
END = date(2026, 1, 13)  # 10 business days
CFG = SimulationConfig(
    initial_cash=Decimal("100000"),
    slippage_bps=Decimal("5"),
    fee_per_trade=Decimal("1.0"),
)


def make_bars(n: int = 10) -> list:
    bars = []
    current = START
    for i in range(n):
        bars.append(make_bar(
            ts=datetime(current.year, current.month, current.day, tzinfo=UTC),
            open=str(150 + i),
            close=str(151 + i),
        ))
        current += timedelta(days=1)
    return bars


class TestBacktestLoopSmoke:
    def _run(self, signals=None):
        bars = make_bars(10)
        if signals is None:
            # Alternate BUY / HOLD
            signals = [
                make_signal(ts=bars[i].timestamp) if i % 2 == 0
                else make_signal(direction=SignalDirection.HOLD, ts=bars[i].timestamp)
                for i in range(len(bars))
            ]

        feed = FakeDataFeed(bars)
        strategy = FakeStrategyAgent(signals)
        risk = FakeRiskManager()
        simulator = ConcreteExecutionSimulator()  # intentional: smoke tests exercise the full stack
        portfolio = InMemoryPortfolio()

        return BacktestLoop(feed, strategy, risk, simulator, portfolio, CFG).run(
            "AAPL", START, END
        )

    def test_returns_at_least_one_fill(self):
        result = self._run()
        fill_events = [e for e in result.events if e.event_type == BacktestEventType.FILL_EXECUTED]
        assert len(fill_events) >= 1

    def test_final_state_differs_from_initial(self):
        result = self._run()
        assert result.final_state != result.initial_state

    def test_fill_executed_timestamp_equals_filled_at(self):
        """FILL_EXECUTED event timestamp must be execution time (fill.filled_at), not signal bar time."""
        result = self._run()
        fill_events = [e for e in result.events if e.event_type == BacktestEventType.FILL_EXECUTED]
        assert len(fill_events) >= 1
        for event in fill_events:
            assert event.fill is not None
            assert event.timestamp == event.fill.filled_at

    def test_no_exceptions_raised(self):
        # Smoke: just confirm the run completes without exception
        result = self._run()
        assert result is not None

    def test_hold_signals_produce_no_fills(self):
        bars = make_bars(5)
        hold_signals = [make_signal(direction=SignalDirection.HOLD, ts=b.timestamp) for b in bars]
        feed = FakeDataFeed(bars)
        strategy = FakeStrategyAgent(hold_signals)
        risk = FakeRiskManager()
        simulator = ConcreteExecutionSimulator()
        portfolio = InMemoryPortfolio()
        result = BacktestLoop(feed, strategy, risk, simulator, portfolio, CFG).run(
            "AAPL", START, date(2026, 1, 6)
        )
        fill_events = [e for e in result.events if e.event_type == BacktestEventType.FILL_EXECUTED]
        assert len(fill_events) == 0

    def test_data_skipped_event_emitted_for_missing_bar(self):
        # Feed has no bars → all days should emit DATA_SKIPPED
        feed = FakeDataFeed([])
        strategy = FakeStrategyAgent([make_signal()])
        risk = FakeRiskManager()
        simulator = ConcreteExecutionSimulator()
        portfolio = InMemoryPortfolio()
        result = BacktestLoop(feed, strategy, risk, simulator, portfolio, CFG).run(
            "AAPL", START, date(2026, 1, 3)
        )
        skip_events = [e for e in result.events if e.event_type == BacktestEventType.DATA_SKIPPED]
        assert len(skip_events) >= 1

    def test_signal_rejected_event_emitted_when_strategy_rejects(self):
        """When strategy returns RejectionReason, loop emits SIGNAL_REJECTED and continues."""
        bars = make_bars(3)
        # First bar: strategy rejects; second and third: BUY signal
        rejection = RejectionReason(code=RejectionCode.INSUFFICIENT_CONTEXT, detail="not enough context")
        signals = [
            rejection,
            make_signal(ts=bars[1].timestamp),
            make_signal(direction=SignalDirection.HOLD, ts=bars[2].timestamp),
        ]

        feed = FakeDataFeed(bars)
        strategy = FakeStrategyAgent(signals)
        risk = FakeRiskManager()
        simulator = ConcreteExecutionSimulator()
        portfolio = InMemoryPortfolio()
        result = BacktestLoop(feed, strategy, risk, simulator, portfolio, CFG).run(
            "AAPL", START, date(2026, 1, 4)
        )

        rejected_events = [e for e in result.events if e.event_type == BacktestEventType.SIGNAL_REJECTED]
        assert len(rejected_events) == 1
        assert rejected_events[0].rejection.code == RejectionCode.INSUFFICIENT_CONTEXT

        # The second bar should still produce a fill (loop continues after rejection)
        fill_events = [e for e in result.events if e.event_type == BacktestEventType.FILL_EXECUTED]
        assert len(fill_events) >= 1
