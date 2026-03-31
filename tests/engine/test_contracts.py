# tests/engine/test_contracts.py
"""Interface compliance tests — isinstance smoke + behavioral rejection paths."""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from tradingagents.engine.contracts.feeds import DataFeed, MarketCalendar
from tradingagents.engine.contracts.strategy import StrategyAgent
from tradingagents.engine.contracts.risk import RiskManager
from tradingagents.engine.contracts.execution import ExecutionSimulator
from tradingagents.engine.contracts.portfolio import Portfolio
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.orders import RejectionCode, RejectionReason
from tradingagents.engine.schemas.portfolio import PortfolioState
from tradingagents.engine.schemas.signals import SignalDirection

from tests.engine.fakes import (
    FakeDataFeed, FakeExecutionSimulator, FakeMarketCalendar,
    FakePortfolio, FakeRiskManager, FakeStrategyAgent,
    make_bar, make_signal,
)

UTC = timezone.utc
NOW = datetime(2026, 1, 2, tzinfo=UTC)
TODAY = NOW.date()
CFG = SimulationConfig(initial_cash=Decimal("100000"))


# ---------------------------------------------------------------------------
# isinstance smoke checks (validates structural shape — not semantics)
# ---------------------------------------------------------------------------

class TestProtocolSmoke:
    def test_fake_data_feed_satisfies_protocol(self):
        assert isinstance(FakeDataFeed([]), DataFeed)

    def test_fake_strategy_satisfies_protocol(self):
        assert isinstance(FakeStrategyAgent([make_signal()]), StrategyAgent)

    def test_fake_calendar_satisfies_protocol(self):
        assert isinstance(FakeMarketCalendar(), MarketCalendar)


class TestABCInstantiation:
    def test_fake_risk_manager_instantiates(self):
        mgr = FakeRiskManager()
        assert isinstance(mgr, RiskManager)

    def test_fake_simulator_instantiates(self):
        sim = FakeExecutionSimulator()
        assert isinstance(sim, ExecutionSimulator)

    def test_fake_portfolio_instantiates(self):
        p = FakePortfolio()
        assert isinstance(p, Portfolio)


# ---------------------------------------------------------------------------
# DataFeed behavioral contracts
# ---------------------------------------------------------------------------

class TestDataFeedContracts:
    def test_stream_bars_yields_data_unavailable_for_missing_date_not_raises(self):
        feed = FakeDataFeed([])  # no bars
        results = list(feed.stream_bars("AAPL", TODAY, TODAY))
        assert len(results) == 1
        assert isinstance(results[0], RejectionReason)
        assert results[0].code == RejectionCode.DATA_UNAVAILABLE

    def test_stream_bars_continues_past_rejection(self):
        bar = make_bar(ts=datetime(2026, 1, 3, tzinfo=UTC))
        feed = FakeDataFeed([bar])
        results = list(feed.stream_bars("AAPL", TODAY, datetime(2026, 1, 3, tzinfo=UTC).date()))
        # Day 1: DATA_UNAVAILABLE (no bar), Day 2: Bar
        assert len(results) == 2
        assert isinstance(results[0], RejectionReason)
        assert isinstance(results[1], type(bar))

    def test_get_bar_returns_data_unavailable_not_raises(self):
        feed = FakeDataFeed([])
        result = feed.get_bar("AAPL", TODAY)
        assert isinstance(result, RejectionReason)
        assert result.code == RejectionCode.DATA_UNAVAILABLE

    def test_get_bar_returns_bar_not_found_for_unknown_symbol(self):
        feed = FakeDataFeed([], missing_symbol="UNKNOWN")
        result = feed.get_bar("UNKNOWN", TODAY)
        assert isinstance(result, RejectionReason)
        assert result.code == RejectionCode.BAR_NOT_FOUND


# ---------------------------------------------------------------------------
# StrategyAgent behavioral contracts
# ---------------------------------------------------------------------------

class TestStrategyAgentContracts:
    def test_returns_insufficient_context_when_configured(self):
        from tradingagents.engine.schemas.orders import RejectionReason, RejectionCode
        rejection = RejectionReason(code=RejectionCode.INSUFFICIENT_CONTEXT)
        agent = FakeStrategyAgent([rejection])
        bar = make_bar(ts=NOW)
        from tradingagents.engine.schemas.market import MarketState
        ms = MarketState(symbol="AAPL", as_of=NOW, latest_bar=bar, bars_window=(bar,))
        result = agent.generate_signal(ms)
        assert isinstance(result, RejectionReason)
        assert result.code == RejectionCode.INSUFFICIENT_CONTEXT


# ---------------------------------------------------------------------------
# RiskManager behavioral contracts
# ---------------------------------------------------------------------------

class TestRiskManagerContracts:
    def _portfolio(self, cash: str = "100000") -> PortfolioState:
        return PortfolioState(
            as_of=NOW, cash=Decimal(cash), positions={}, cost_basis={}
        )

    def test_approves_valid_signal(self):
        mgr = FakeRiskManager()
        signal = make_signal(confidence=0.8)
        result = mgr.evaluate(signal, self._portfolio(), {"AAPL": Decimal("150")}, CFG)
        from tradingagents.engine.schemas.orders import ApprovedOrder
        assert isinstance(result, ApprovedOrder)

    def test_returns_insufficient_cash_when_portfolio_empty(self):
        mgr = FakeRiskManager()
        signal = make_signal(confidence=0.8)
        # zero cash → computed size = 0 → INSUFFICIENT_CASH
        result = mgr.evaluate(signal, self._portfolio("0"), {"AAPL": Decimal("150")}, CFG)
        assert isinstance(result, RejectionReason)
        assert result.code == RejectionCode.INSUFFICIENT_CASH

    def test_compute_position_size_uses_mark_to_market_equity(self):
        mgr = FakeRiskManager()
        signal = make_signal(confidence=1.0)
        portfolio = PortfolioState(
            as_of=NOW, cash=Decimal("0"),
            positions={"AAPL": Decimal("10")},
            cost_basis={"AAPL": Decimal("100")},
        )
        prices = {"AAPL": Decimal("200")}
        size = mgr.compute_position_size(signal, portfolio, prices, CFG)
        # equity = 0 cash + 10 * 200 = 2000; max_position_pct = 0.10; confidence = 1.0
        # dollar_notional = 1.0 * 0.10 * 2000 = 200.00
        assert size == Decimal("200.00")


# ---------------------------------------------------------------------------
# ExecutionSimulator behavioral contracts
# ---------------------------------------------------------------------------

class TestExecutionSimulatorContracts:
    def _order(self) -> "ApprovedOrder":
        from tradingagents.engine.schemas.orders import Order, ApprovedOrder
        order = Order(
            id=uuid4(), symbol="AAPL",
            direction=SignalDirection.BUY,
            quantity=Decimal("10"),
            created_at=NOW,
        )
        return ApprovedOrder(order=order, approved_at=NOW, approved_quantity=Decimal("10"))

    def test_returns_no_next_bar_when_next_bar_is_none(self):
        sim = FakeExecutionSimulator()
        result = sim.fill(self._order(), None, FakeMarketCalendar(), CFG)
        assert isinstance(result, RejectionReason)
        assert result.code == RejectionCode.NO_NEXT_BAR

    def test_returns_market_closed_when_calendar_rejects(self):
        class ClosedCalendar:
            def is_trading_day(self, dt): return False
            def next_trading_day(self, dt): return dt + timedelta(days=1)
            def previous_trading_day(self, dt): return dt - timedelta(days=1)
            def is_session_open(self, dt): return False

        sim = FakeExecutionSimulator()
        bar = make_bar(ts=datetime(2026, 1, 3, tzinfo=UTC))
        result = sim.fill(self._order(), bar, ClosedCalendar(), CFG)
        assert isinstance(result, RejectionReason)
        assert result.code == RejectionCode.MARKET_CLOSED

    def test_no_next_bar_takes_precedence_over_market_closed(self):
        """When next_bar is None, must return NO_NEXT_BAR even if calendar is also 'closed'."""
        class ClosedCalendar:
            def is_trading_day(self, dt): return False
            def next_trading_day(self, dt): return dt + timedelta(days=1)
            def previous_trading_day(self, dt): return dt - timedelta(days=1)
            def is_session_open(self, dt): return False

        sim = FakeExecutionSimulator()
        result = sim.fill(self._order(), None, ClosedCalendar(), CFG)
        assert result.code == RejectionCode.NO_NEXT_BAR  # not MARKET_CLOSED


# ---------------------------------------------------------------------------
# Portfolio behavioral contracts
# ---------------------------------------------------------------------------

class TestPortfolioContracts:
    def _state(self) -> PortfolioState:
        return PortfolioState(
            as_of=NOW, cash=Decimal("100000"), positions={}, cost_basis={}
        )

    def _fill(self) -> "FillResult":
        from tradingagents.engine.schemas.orders import FillResult
        return FillResult(
            order_id=uuid4(), symbol="AAPL",
            direction=SignalDirection.BUY,
            approved_quantity=Decimal("10"),
            filled_quantity=Decimal("10"),
            fill_price=Decimal("150.00"),
            slippage=Decimal("0"),
            fees=Decimal("0"),
            filled_at=datetime(2026, 1, 3, tzinfo=UTC),
        )

    def test_apply_fill_is_pure_same_input_same_output(self):
        p = FakePortfolio()
        state = self._state()
        fill = self._fill()
        result1 = p.apply_fill(state, fill)
        result2 = p.apply_fill(state, fill)
        assert result1 == result2

    def test_apply_fill_does_not_mutate_input(self):
        p = FakePortfolio()
        state = self._state()
        original_cash = state.cash
        p.apply_fill(state, self._fill())
        assert state.cash == original_cash  # unchanged

    def test_initial_state_uses_supplied_as_of(self):
        p = FakePortfolio()
        state = Portfolio.initial_state(CFG, as_of=NOW)
        assert state.as_of == NOW
        assert state.cash == CFG.initial_cash
        assert state.positions == {}


# ---------------------------------------------------------------------------
# ConcreteExecutionSimulator behavioral contracts
# ---------------------------------------------------------------------------

from tradingagents.engine.runtime.simulator import ConcreteExecutionSimulator


class TestConcreteExecutionSimulator:
    def _order(self, direction=SignalDirection.BUY, qty="10") -> "ApprovedOrder":
        from tradingagents.engine.schemas.orders import Order, ApprovedOrder
        order = Order(
            id=uuid4(), symbol="AAPL", direction=direction,
            quantity=Decimal(qty), created_at=NOW,
        )
        return ApprovedOrder(order=order, approved_at=NOW, approved_quantity=Decimal(qty))

    def test_fill_at_next_open_plus_slippage_for_buy(self):
        sim = ConcreteExecutionSimulator()
        cfg = SimulationConfig(initial_cash=Decimal("100000"), slippage_bps=Decimal("10"))
        bar = make_bar(ts=datetime(2026, 1, 3, tzinfo=UTC), open="150.00")
        result = sim.fill(self._order(), bar, FakeMarketCalendar(), cfg)
        from tradingagents.engine.schemas.orders import FillResult
        assert isinstance(result, FillResult)
        # slippage = 150.00 * 10 / 10000 = 0.1500
        # fill_price = 150.00 + 0.15 = 150.15
        assert result.fill_price == Decimal("150.15")
        assert result.slippage == Decimal("0.1500")

    def test_fill_sell_subtracts_slippage(self):
        sim = ConcreteExecutionSimulator()
        cfg = SimulationConfig(initial_cash=Decimal("100000"), slippage_bps=Decimal("10"))
        bar = make_bar(ts=datetime(2026, 1, 3, tzinfo=UTC), open="150.00")
        result = sim.fill(self._order(SignalDirection.SELL), bar, FakeMarketCalendar(), cfg)
        from tradingagents.engine.schemas.orders import FillResult
        assert isinstance(result, FillResult)
        assert result.fill_price == Decimal("149.8500")

    def test_fees_are_additive_flat_plus_bps(self):
        sim = ConcreteExecutionSimulator()
        cfg = SimulationConfig(
            initial_cash=Decimal("100000"),
            slippage_bps=Decimal("0"),
            fee_per_trade=Decimal("1.0"),
            fee_bps=Decimal("10"),  # 10 bps = 0.1%
        )
        bar = make_bar(ts=datetime(2026, 1, 3, tzinfo=UTC), open="100.00")
        result = sim.fill(self._order(qty="10"), bar, FakeMarketCalendar(), cfg)
        from tradingagents.engine.schemas.orders import FillResult
        # notional = 10 * 100 = 1000; bps_fee = 1000 * 10 / 10000 = 1.00
        # total_fees = 1.0 (flat) + 1.0 (bps) = 2.0
        assert isinstance(result, FillResult)
        assert result.fees == Decimal("2.0")


# ---------------------------------------------------------------------------
# InMemoryPortfolio behavioral contracts
# ---------------------------------------------------------------------------

from tradingagents.engine.runtime.paper_portfolio import InMemoryPortfolio


class TestInMemoryPortfolio:
    def _state(self, cash="100000") -> PortfolioState:
        return PortfolioState(
            as_of=NOW, cash=Decimal(cash), positions={}, cost_basis={}
        )

    def _fill(self, direction=SignalDirection.BUY, qty="10", price="150.00", fees="1.00"):
        from tradingagents.engine.schemas.orders import FillResult
        return FillResult(
            order_id=uuid4(), symbol="AAPL", direction=direction,
            approved_quantity=Decimal(qty), filled_quantity=Decimal(qty),
            fill_price=Decimal(price), slippage=Decimal("0"), fees=Decimal(fees),
            filled_at=datetime(2026, 1, 3, tzinfo=UTC),
        )

    def test_buy_reduces_cash_and_adds_position(self):
        p = InMemoryPortfolio()
        state = self._state()
        fill = self._fill()  # BUY 10 @ 150.00 + 1.00 fee
        new_state = p.apply_fill(state, fill)
        # cash = 100000 - 10*150 - 1 = 98499
        assert new_state.cash == Decimal("98499")
        assert new_state.positions["AAPL"] == Decimal("10")

    def test_sell_adds_cash_and_removes_position(self):
        p = InMemoryPortfolio()
        state = PortfolioState(
            as_of=NOW, cash=Decimal("0"),
            positions={"AAPL": Decimal("10")},
            cost_basis={"AAPL": Decimal("150.00")},
        )
        fill = self._fill(SignalDirection.SELL, fees="0")  # SELL 10 @ 150 + 0 fee
        new_state = p.apply_fill(state, fill)
        assert new_state.cash == Decimal("1500")
        assert "AAPL" not in new_state.positions

    def test_mark_to_market_computes_equity(self):
        p = InMemoryPortfolio()
        state = PortfolioState(
            as_of=NOW, cash=Decimal("85000"),
            positions={"AAPL": Decimal("10")},
            cost_basis={"AAPL": Decimal("150.00")},
        )
        metrics = p.mark_to_market(state, {"AAPL": Decimal("160.00")})
        # equity = 85000 + 10 * 160 = 86600
        assert metrics.total_equity == Decimal("86600")
        # unrealized_pnl = 10 * (160 - 150) = 100
        assert metrics.unrealized_pnl == Decimal("100")

    def test_apply_fill_is_pure(self):
        p = InMemoryPortfolio()
        state = self._state()
        fill = self._fill()
        r1 = p.apply_fill(state, fill)
        r2 = p.apply_fill(state, fill)
        assert r1 == r2
        assert state.cash == Decimal("100000")  # input unchanged
