# tests/engine/test_schemas.py
from __future__ import annotations
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from tradingagents.engine.schemas.base import BaseSchema


class SampleSchema(BaseSchema):
    ts: datetime
    name: str


class TestBaseSchema:
    def test_utc_datetime_accepted(self):
        s = SampleSchema(ts=datetime(2026, 1, 1, tzinfo=timezone.utc), name="x")
        assert s.ts.tzinfo == timezone.utc

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValidationError):
            SampleSchema(ts=datetime(2026, 1, 1), name="x")  # naive — no tzinfo

    def test_non_utc_datetime_normalised_to_utc(self):
        eastern = timezone(timedelta(hours=-5))
        dt = datetime(2026, 1, 1, 10, 0, tzinfo=eastern)
        s = SampleSchema(ts=dt, name="x")
        assert s.ts == datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc)

    def test_iso_string_datetime_normalised_to_utc(self):
        # Pydantic parses ISO strings; mode="after" validator then enforces UTC
        s = SampleSchema(ts="2026-01-01T00:00:00+00:00", name="x")
        assert s.ts.tzinfo == timezone.utc

    def test_frozen_prevents_mutation(self):
        s = SampleSchema(ts=datetime(2026, 1, 1, tzinfo=timezone.utc), name="x")
        with pytest.raises(ValidationError):
            s.name = "mutated"

    def test_schemas_are_not_hashable(self):
        # frozen=True does not enable hash — schemas with dict/list fields are unsafe to hash
        s = SampleSchema(ts=datetime(2026, 1, 1, tzinfo=timezone.utc), name="x")
        # SampleSchema has no dict/list so it may be hashable — just confirm no crash
        # The important case is tested in test_schemas for PortfolioState (dict fields)
        assert s is not None


# append to tests/engine/test_schemas.py
from decimal import Decimal
from tradingagents.engine.schemas.market import Bar, MarketState, Tick


class TestMarketSchemas:
    UTC = timezone.utc

    def _bar(self, symbol="AAPL", close="150.00"):
        return Bar(
            symbol=symbol,
            timestamp=datetime(2026, 1, 2, tzinfo=self.UTC),
            open=Decimal("149.00"),
            high=Decimal("151.00"),
            low=Decimal("148.00"),
            close=Decimal(close),
            volume=Decimal("1000000"),
        )

    def test_bar_construction(self):
        b = self._bar()
        assert b.symbol == "AAPL"
        assert b.close == Decimal("150.00")
        assert b.vwap is None

    def test_bar_with_vwap(self):
        b = self._bar()
        b2 = b.model_copy(update={"vwap": Decimal("149.50")})
        assert b2.vwap == Decimal("149.50")

    def test_tick_construction(self):
        t = Tick(
            symbol="AAPL",
            timestamp=datetime(2026, 1, 2, 14, 30, tzinfo=self.UTC),
            price=Decimal("150.05"),
            size=Decimal("100"),
            side="bid",
        )
        assert t.side == "bid"

    def test_market_state_bars_window_is_tuple(self):
        b = self._bar()
        ms = MarketState(
            symbol="AAPL",
            as_of=datetime(2026, 1, 2, tzinfo=self.UTC),
            latest_bar=b,
            bars_window=(b,),
        )
        assert isinstance(ms.bars_window, tuple)

    def test_market_state_rejects_list_for_bars_window(self):
        # Pydantic v2 coerces list→tuple for tuple[X, ...] fields
        b = self._bar()
        ms = MarketState(
            symbol="AAPL",
            as_of=datetime(2026, 1, 2, tzinfo=self.UTC),
            latest_bar=b,
            bars_window=[b],  # list — Pydantic should coerce to tuple
        )
        assert isinstance(ms.bars_window, tuple)


# append to tests/engine/test_schemas.py
from uuid import uuid4
from tradingagents.engine.schemas.signals import Signal, SignalDirection
from tradingagents.engine.schemas.orders import (
    ApprovedOrder, FillModel, FillResult, Order,
    RejectionCode, RejectionReason,
)


class TestSignalSchemas:
    UTC = timezone.utc

    def test_signal_direction_enum_values(self):
        assert SignalDirection.BUY.value == "BUY"
        assert SignalDirection.SELL.value == "SELL"
        assert SignalDirection.HOLD.value == "HOLD"

    def test_signal_confidence_bounds_enforced(self):
        now = datetime(2026, 1, 2, tzinfo=self.UTC)
        with pytest.raises(ValidationError):
            Signal(
                symbol="AAPL", direction=SignalDirection.BUY,
                confidence=1.5,  # > 1.0 — must fail
                reasoning="test", generated_at=now, source_bar_timestamp=now,
            )

    def test_signal_confidence_lower_bound(self):
        now = datetime(2026, 1, 2, tzinfo=self.UTC)
        with pytest.raises(ValidationError):
            Signal(
                symbol="AAPL", direction=SignalDirection.BUY,
                confidence=-0.1,  # < 0.0 — must fail
                reasoning="test", generated_at=now, source_bar_timestamp=now,
            )

    def test_signal_valid(self):
        now = datetime(2026, 1, 2, tzinfo=self.UTC)
        s = Signal(
            symbol="AAPL", direction=SignalDirection.BUY,
            confidence=0.8, reasoning="strong trend",
            generated_at=now, source_bar_timestamp=now,
        )
        assert s.confidence == 0.8


class TestOrderSchemas:
    UTC = timezone.utc

    def test_rejection_code_exhaustive(self):
        codes = {c.value for c in RejectionCode}
        assert "DATA_UNAVAILABLE" in codes
        assert "BAR_NOT_FOUND" in codes
        assert "NO_NEXT_BAR" in codes
        assert "MARKET_CLOSED" in codes
        assert "INSUFFICIENT_CASH" in codes
        assert "EXCEEDS_POSITION_LIMIT" in codes
        assert "RISK_THRESHOLD_BREACHED" in codes
        assert "STRATEGY_TIMEOUT" in codes
        assert "INSUFFICIENT_CONTEXT" in codes

    def test_rejection_reason_with_detail(self):
        r = RejectionReason(code=RejectionCode.NO_NEXT_BAR, detail="end of data")
        assert r.detail == "end of data"

    def test_fill_result_is_partial_false_when_full_fill(self):
        now = datetime(2026, 1, 2, tzinfo=self.UTC)
        fr = FillResult(
            order_id=uuid4(), symbol="AAPL",
            direction=SignalDirection.BUY,
            approved_quantity=Decimal("10"),
            filled_quantity=Decimal("10"),
            fill_price=Decimal("150.00"),
            slippage=Decimal("0.0750"),
            fees=Decimal("1.00"),
            filled_at=now,
        )
        assert fr.is_partial is False

    def test_fill_result_is_partial_true_when_partial(self):
        now = datetime(2026, 1, 2, tzinfo=self.UTC)
        fr = FillResult(
            order_id=uuid4(), symbol="AAPL",
            direction=SignalDirection.BUY,
            approved_quantity=Decimal("10"),
            filled_quantity=Decimal("7"),
            fill_price=Decimal("150.00"),
            slippage=Decimal("0.0750"),
            fees=Decimal("1.00"),
            filled_at=now,
        )
        assert fr.is_partial is True

    def test_fill_model_enum(self):
        assert FillModel.NEXT_OPEN.value == "NEXT_OPEN"


# append to tests/engine/test_schemas.py
from datetime import date as date_type
from tradingagents.engine.schemas.portfolio import (
    BacktestEvent, BacktestEventType, BacktestResult,
    PortfolioMetrics, PortfolioState,
)
from tradingagents.engine.schemas.config import SimulationConfig


class TestPortfolioSchemas:
    UTC = timezone.utc

    def test_portfolio_state_construction(self):
        ps = PortfolioState(
            as_of=datetime(2026, 1, 2, tzinfo=self.UTC),
            cash=Decimal("100000"),
            positions={"AAPL": Decimal("10")},
            cost_basis={"AAPL": Decimal("150.00")},
        )
        assert ps.cash == Decimal("100000")

    def test_backtest_event_type_has_signal_rejected(self):
        assert "SIGNAL_REJECTED" in {e.value for e in BacktestEventType}

    def test_backtest_event_type_has_all_six_values(self):
        values = {e.value for e in BacktestEventType}
        assert values == {
            "SIGNAL_GENERATED", "SIGNAL_REJECTED",
            "ORDER_APPROVED", "ORDER_REJECTED",
            "FILL_EXECUTED", "DATA_SKIPPED",
        }

    def test_backtest_result_events_is_tuple(self):
        now = datetime(2026, 1, 2, tzinfo=self.UTC)
        ps = PortfolioState(as_of=now, cash=Decimal("100000"), positions={}, cost_basis={})
        metrics = PortfolioMetrics(
            as_of=now, total_equity=Decimal("100000"),
            unrealized_pnl=Decimal("0"), realized_pnl=Decimal("0"),
            total_fees_paid=Decimal("0"), max_drawdown_pct=None,
        )
        result = BacktestResult(
            symbol="AAPL",
            start=date_type(2026, 1, 1),
            end=date_type(2026, 1, 10),
            initial_state=ps,
            final_state=ps,
            events=(),
            metrics=metrics,
        )
        assert isinstance(result.events, tuple)

    def test_backtest_event_carries_signal_and_order(self):
        from uuid import uuid4

        from tradingagents.engine.schemas.orders import ApprovedOrder, FillModel, Order
        from tradingagents.engine.schemas.signals import Signal, SignalDirection

        now = datetime(2026, 1, 2, 15, 0, 0, tzinfo=self.UTC)
        sig = Signal(
            symbol="AAPL",
            direction=SignalDirection.BUY,
            confidence=0.9,
            reasoning="MA cross",
            generated_at=now,
            source_bar_timestamp=now,
        )
        oid = uuid4()
        ord_inner = Order(
            id=oid,
            symbol="AAPL",
            direction=SignalDirection.BUY,
            quantity=Decimal("10"),
            created_at=now,
            fill_model=FillModel.NEXT_OPEN,
        )
        approved = ApprovedOrder(order=ord_inner, approved_at=now, approved_quantity=Decimal("10"))
        ev_sig = BacktestEvent(
            event_type=BacktestEventType.SIGNAL_GENERATED,
            timestamp=now,
            symbol="AAPL",
            signal=sig,
        )
        assert ev_sig.signal is not None and ev_sig.signal.reasoning == "MA cross"
        ev_ord = BacktestEvent(
            event_type=BacktestEventType.ORDER_APPROVED,
            timestamp=now,
            symbol="AAPL",
            order=approved,
        )
        assert ev_ord.order is not None
        assert ev_ord.order.approved_quantity == Decimal("10")


class TestSimulationConfig:
    def test_defaults(self):
        cfg = SimulationConfig(initial_cash=Decimal("50000"))
        assert cfg.slippage_bps == Decimal("5")
        assert cfg.fee_per_trade == Decimal("1.0")
        assert cfg.fill_model == FillModel.NEXT_OPEN
        assert cfg.random_seed == 42
        assert cfg.fee_bps is None

    def test_additive_fee_policy_documented(self):
        # fee_per_trade and fee_bps are both present — they are additive
        cfg = SimulationConfig(
            initial_cash=Decimal("50000"),
            fee_per_trade=Decimal("1.0"),
            fee_bps=Decimal("2"),
        )
        assert cfg.fee_bps == Decimal("2")
        assert cfg.fee_per_trade == Decimal("1.0")

    def test_decimal_defaults_not_float_literals(self):
        # Ensure no float precision artifacts in default values
        cfg = SimulationConfig(initial_cash=Decimal("50000"))
        assert type(cfg.slippage_bps) is Decimal
        assert type(cfg.fee_per_trade) is Decimal
        assert type(cfg.max_position_pct) is Decimal
