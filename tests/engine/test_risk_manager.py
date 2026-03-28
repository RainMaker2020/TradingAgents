# tests/engine/test_risk_manager.py
"""Unit tests for ConcreteRiskManager."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from tradingagents.engine.runtime.risk_manager import ConcreteRiskManager
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.orders import ApprovedOrder, RejectionCode
from tradingagents.engine.schemas.portfolio import PortfolioState
from tradingagents.engine.schemas.signals import SignalDirection

from tests.engine.fakes import make_signal

UTC = timezone.utc
NOW = datetime(2026, 1, 2, tzinfo=UTC)
CFG = SimulationConfig(initial_cash=Decimal("100000"), min_confidence_threshold=0.5)
PRICES = {"AAPL": Decimal("150")}


def _portfolio(cash: str = "100000", positions: dict | None = None) -> PortfolioState:
    return PortfolioState(
        as_of=NOW,
        cash=Decimal(cash),
        positions={k: Decimal(v) for k, v in (positions or {}).items()},
        cost_basis={k: Decimal("150") for k in (positions or {})},
    )


class TestConcreteRiskManager:
    def test_approves_signal_above_threshold(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8)
        result = mgr.evaluate(signal, _portfolio(), PRICES, CFG)
        assert isinstance(result, ApprovedOrder)

    def test_rejects_signal_below_confidence_threshold(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.3)  # below 0.5 threshold
        result = mgr.evaluate(signal, _portfolio(), PRICES, CFG)
        assert result.code == RejectionCode.RISK_THRESHOLD_BREACHED

    def test_rejects_when_cash_exhausted(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8)
        result = mgr.evaluate(signal, _portfolio(cash="0"), PRICES, CFG)
        assert result.code == RejectionCode.INSUFFICIENT_CASH

    def test_rejects_when_position_limit_reached(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8)
        # 100 shares × $150 = $15,000 > 10% of $100,000 equity ($10,000)
        portfolio = _portfolio(positions={"AAPL": "100"})
        result = mgr.evaluate(signal, portfolio, PRICES, CFG)
        assert result.code == RejectionCode.EXCEEDS_POSITION_LIMIT

    def test_rejects_when_price_missing(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8)
        result = mgr.evaluate(signal, _portfolio(), {}, CFG)
        assert result.code == RejectionCode.INSUFFICIENT_CASH

    def test_approved_quantity_respects_cash_cap(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8)
        # Only $1000 cash — can afford at most ~6 shares at $150
        result = mgr.evaluate(signal, _portfolio(cash="1000"), PRICES, CFG)
        assert isinstance(result, ApprovedOrder)
        assert result.approved_quantity * Decimal("150") <= Decimal("1000")

    def test_approved_quantity_respects_position_limit(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8)
        # 50 shares × $150 = $7,500 position; cash = $100,000; total equity = $107,500
        # max allowed = 10% × $107,500 = $10,750; headroom = $10,750 - $7,500 = $3,250
        portfolio = _portfolio(positions={"AAPL": "50"})
        position_value = Decimal("50") * Decimal("150")
        total_equity = Decimal("100000") + position_value
        max_allowed = CFG.max_position_pct * total_equity
        result = mgr.evaluate(signal, portfolio, PRICES, CFG)
        assert isinstance(result, ApprovedOrder)
        # Total position after fill must not exceed max_allowed_value
        new_total = (Decimal("50") + result.approved_quantity) * Decimal("150")
        assert new_total <= max_allowed + Decimal("1")  # allow 1-cent rounding

    def test_rejects_sell_signal_with_no_position(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8, direction=SignalDirection.SELL)
        # No AAPL position — should reject before sizing
        result = mgr.evaluate(signal, _portfolio(), PRICES, CFG)
        assert result.code == RejectionCode.EXCEEDS_POSITION_LIMIT
        assert "no position" in result.detail

    def test_approves_sell_signal_with_existing_position(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8, direction=SignalDirection.SELL)
        # Portfolio holds 10 AAPL shares — there is something to sell
        portfolio = _portfolio(positions={"AAPL": "10"})
        result = mgr.evaluate(signal, portfolio, PRICES, CFG)
        assert isinstance(result, ApprovedOrder)
        assert result.order.direction == SignalDirection.SELL
        assert result.approved_quantity > Decimal("0")

    def test_approves_sell_with_zero_cash_when_position_exists(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8, direction=SignalDirection.SELL)
        # Cash exhausted, but holding 10 AAPL — SELL should not require cash
        portfolio = _portfolio(cash="0", positions={"AAPL": "10"})
        result = mgr.evaluate(signal, portfolio, PRICES, CFG)
        assert isinstance(result, ApprovedOrder)
        assert result.order.direction == SignalDirection.SELL
        assert result.approved_quantity > Decimal("0")

    def test_rejects_buy_when_drawdown_exceeds_limit(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8, direction=SignalDirection.BUY)
        cfg = SimulationConfig(
            initial_cash=Decimal("100000"),
            min_confidence_threshold=0.5,
            max_drawdown_limit=Decimal("0.10"),
        )
        portfolio = PortfolioState(
            as_of=NOW,
            cash=Decimal("50000"),
            positions={},
            cost_basis={},
        )
        result = mgr.evaluate(
            signal,
            portfolio,
            PRICES,
            cfg,
            peak_equity_for_drawdown=Decimal("100000"),
        )
        assert result.code == RejectionCode.DRAWDOWN_LIMIT_BREACHED

    def test_buy_allowed_when_drawdown_within_limit(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=0.8, direction=SignalDirection.BUY)
        cfg = SimulationConfig(
            initial_cash=Decimal("100000"),
            min_confidence_threshold=0.5,
            max_drawdown_limit=Decimal("0.50"),
        )
        portfolio = PortfolioState(
            as_of=NOW,
            cash=Decimal("50000"),
            positions={},
            cost_basis={},
        )
        result = mgr.evaluate(
            signal,
            portfolio,
            PRICES,
            cfg,
            peak_equity_for_drawdown=Decimal("100000"),
        )
        assert isinstance(result, ApprovedOrder)

    def test_max_position_size_caps_buy_quantity(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=1.0, direction=SignalDirection.BUY)
        cfg = SimulationConfig(
            initial_cash=Decimal("100000"),
            min_confidence_threshold=0.5,
            max_position_pct=Decimal("1.0"),
            max_position_size=Decimal("3"),
        )
        result = mgr.evaluate(signal, _portfolio(), PRICES, cfg)
        assert isinstance(result, ApprovedOrder)
        assert result.approved_quantity <= Decimal("3")

    def test_buy_rejected_when_at_max_position_size(self):
        mgr = ConcreteRiskManager()
        signal = make_signal(confidence=1.0, direction=SignalDirection.BUY)
        cfg = SimulationConfig(
            initial_cash=Decimal("100000"),
            min_confidence_threshold=0.5,
            max_position_pct=Decimal("1.0"),
            max_position_size=Decimal("100"),
        )
        portfolio = _portfolio(positions={"AAPL": "100"})
        result = mgr.evaluate(signal, portfolio, PRICES, cfg)
        assert result.code == RejectionCode.EXCEEDS_POSITION_LIMIT
