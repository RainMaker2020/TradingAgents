# tests/engine/fakes.py
"""Shared deterministic test doubles for the engine test suite."""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterator, Union
import uuid

from tradingagents.engine.contracts.execution import ExecutionSimulator
from tradingagents.engine.contracts.portfolio import Portfolio
from tradingagents.engine.contracts.risk import RiskManager
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.market import Bar, MarketState
from tradingagents.engine.schemas.orders import (
    ApprovedOrder, FillModel, FillResult, Order,
    RejectionCode, RejectionReason,
)
from tradingagents.engine.schemas.portfolio import (
    PortfolioMetrics, PortfolioState,
)
from tradingagents.engine.schemas.signals import Signal, SignalDirection

UTC = timezone.utc


# ---------------------------------------------------------------------------
# FakeBar: factory helper
# ---------------------------------------------------------------------------

def make_bar(
    symbol: str = "AAPL",
    ts: datetime | None = None,
    open: str = "150.00",
    close: str = "151.00",
) -> Bar:
    ts = ts or datetime(2026, 1, 2, tzinfo=UTC)
    p = Decimal(open)
    return Bar(
        symbol=symbol, timestamp=ts,
        open=p, high=p + Decimal("1"), low=p - Decimal("1"),
        close=Decimal(close), volume=Decimal("1000000"),
    )


# ---------------------------------------------------------------------------
# FakeMarketCalendar: all days are trading days; fully deterministic
# ---------------------------------------------------------------------------

class FakeMarketCalendar:
    """All days are trading days. is_session_open always True.
    Structurally satisfies MarketCalendar Protocol.
    """
    def is_trading_day(self, dt: date) -> bool:
        return True

    def next_trading_day(self, dt: date) -> date:
        return dt + timedelta(days=1)

    def previous_trading_day(self, dt: date) -> date:
        return dt - timedelta(days=1)

    def is_session_open(self, dt: datetime) -> bool:
        return True


# ---------------------------------------------------------------------------
# FakeDataFeed: yields pre-supplied bars; returns DATA_UNAVAILABLE for gaps
# ---------------------------------------------------------------------------

class FakeDataFeed:
    """In-memory DataFeed. Structurally satisfies DataFeed Protocol.

    Args:
        bars: ordered list of Bar objects to yield.
        missing_symbol: if get_bar is called for this symbol, return BAR_NOT_FOUND.
    """
    def __init__(self, bars: list[Bar], missing_symbol: str = "") -> None:
        self._bars = {b.timestamp.date(): b for b in bars}
        self._missing_symbol = missing_symbol
        self.calendar = FakeMarketCalendar()

    def stream_bars(
        self, symbol: str, start: date, end: date
    ) -> Iterator[Union[Bar, RejectionReason]]:
        current = start
        while current <= end:
            if symbol == self._missing_symbol:
                yield RejectionReason(code=RejectionCode.BAR_NOT_FOUND)
                current += timedelta(days=1)
                continue
            bar = self._bars.get(current)
            if bar is not None:
                yield bar
            else:
                yield RejectionReason(code=RejectionCode.DATA_UNAVAILABLE)
            current += timedelta(days=1)

    def get_bar(self, symbol: str, as_of: date) -> Union[Bar, RejectionReason]:
        if symbol == self._missing_symbol:
            return RejectionReason(code=RejectionCode.BAR_NOT_FOUND)
        bar = self._bars.get(as_of)
        if bar is None:
            return RejectionReason(code=RejectionCode.DATA_UNAVAILABLE)
        return bar


# ---------------------------------------------------------------------------
# FakeStrategyAgent: returns fixed Signal or RejectionReason
# ---------------------------------------------------------------------------

class FakeStrategyAgent:
    """Returns a pre-configured Signal or RejectionReason.
    Structurally satisfies StrategyAgent Protocol.

    Args:
        signals: list of Union[Signal, RejectionReason] to cycle through.
    """
    def __init__(self, signals: list[Union[Signal, RejectionReason]]) -> None:
        self._signals = signals
        self._idx = 0

    def generate_signal(
        self, market_state: MarketState
    ) -> Union[Signal, RejectionReason]:
        result = self._signals[self._idx % len(self._signals)]
        self._idx += 1
        return result


def make_signal(
    symbol: str = "AAPL",
    direction: SignalDirection = SignalDirection.BUY,
    confidence: float = 0.8,
    ts: datetime | None = None,
) -> Signal:
    ts = ts or datetime(2026, 1, 2, tzinfo=UTC)
    return Signal(
        symbol=symbol, direction=direction, confidence=confidence,
        reasoning="fake signal", generated_at=ts, source_bar_timestamp=ts,
    )


# ---------------------------------------------------------------------------
# FakeRiskManager: approves all signals at full quantity
# ---------------------------------------------------------------------------

class FakeRiskManager(RiskManager):
    """Approves every signal. Returns ApprovedOrder at compute_position_size qty.

    Uses a counter-based deterministic UUID for order IDs to ensure two runs
    with the same inputs produce identical FillResult.order_id values.
    """

    def __init__(self) -> None:
        self._order_counter = 0

    def evaluate(
        self,
        signal: Signal,
        portfolio: PortfolioState,
        current_prices: dict[str, Decimal],
        config: SimulationConfig,
    ) -> Union[ApprovedOrder, RejectionReason]:
        dollar_notional = self.compute_position_size(signal, portfolio, current_prices, config)
        price = current_prices.get(signal.symbol, Decimal("0"))
        if price <= Decimal("0"):
            return RejectionReason(
                code=RejectionCode.INSUFFICIENT_CASH,
                detail="no price available for symbol",
            )
        qty = (dollar_notional / price).quantize(Decimal("0.000001"))
        if qty <= Decimal("0"):
            return RejectionReason(
                code=RejectionCode.INSUFFICIENT_CASH,
                detail="computed size <= 0",
            )
        order_id = uuid.UUID(int=self._order_counter)
        self._order_counter += 1
        order = Order(
            id=order_id, symbol=signal.symbol, direction=signal.direction,
            quantity=qty, created_at=signal.generated_at,
            fill_model=FillModel.NEXT_OPEN,
            signal_ref=None,
        )
        return ApprovedOrder(
            order=order,
            approved_at=signal.generated_at,
            approved_quantity=qty,
        )


# ---------------------------------------------------------------------------
# FakeExecutionSimulator: fills at next_bar.open, zero slippage, zero fees
# ---------------------------------------------------------------------------

class FakeExecutionSimulator(ExecutionSimulator):
    """Fills at next_bar.open, zero slippage, zero fees.
    Still enforces NO_NEXT_BAR and MARKET_CLOSED precedence.
    """

    def fill(
        self,
        order: ApprovedOrder,
        next_bar: Bar | None,
        calendar,
        config: SimulationConfig,
    ) -> Union[FillResult, RejectionReason]:
        if next_bar is None:
            return RejectionReason(code=RejectionCode.NO_NEXT_BAR)
        if not calendar.is_trading_day(next_bar.timestamp.date()):
            return RejectionReason(code=RejectionCode.MARKET_CLOSED)
        return FillResult(
            order_id=order.order.id,
            symbol=order.order.symbol,
            direction=order.order.direction,
            approved_quantity=order.approved_quantity,
            filled_quantity=order.approved_quantity,
            fill_price=next_bar.open,
            slippage=Decimal("0"),
            fees=Decimal("0"),
            filled_at=next_bar.timestamp,
        )


# ---------------------------------------------------------------------------
# FakePortfolio: simple cash/position arithmetic
# ---------------------------------------------------------------------------

class FakePortfolio(Portfolio):
    """Tracks cash and positions. BUY subtracts cash; SELL adds cash."""

    def apply_fill(self, state: PortfolioState, fill: FillResult) -> PortfolioState:
        positions = dict(state.positions)
        cost_basis = dict(state.cost_basis)
        cash = state.cash

        current_qty = positions.get(fill.symbol, Decimal("0"))
        notional = fill.filled_quantity * fill.fill_price

        if fill.direction == SignalDirection.BUY:
            new_qty = current_qty + fill.filled_quantity
            cash = cash - notional - fill.fees
            # weighted average cost basis
            total_cost = current_qty * cost_basis.get(fill.symbol, Decimal("0")) + notional
            cost_basis[fill.symbol] = (total_cost / new_qty).quantize(Decimal("0.0001"))
        else:  # SELL
            new_qty = current_qty - fill.filled_quantity
            cash = cash + notional - fill.fees
            if new_qty == Decimal("0"):
                cost_basis.pop(fill.symbol, None)

        if new_qty > Decimal("0"):
            positions[fill.symbol] = new_qty
        else:
            positions.pop(fill.symbol, None)

        return PortfolioState(
            as_of=fill.filled_at,
            cash=cash,
            positions=positions,
            cost_basis=cost_basis,
        )

    def mark_to_market(
        self, state: PortfolioState, prices: dict[str, Decimal]
    ) -> PortfolioMetrics:
        position_value = sum(
            qty * prices.get(sym, state.cost_basis.get(sym, Decimal("0")))
            for sym, qty in state.positions.items()
        )
        total_equity = state.cash + position_value
        unrealized_pnl = sum(
            qty * (prices.get(sym, Decimal("0")) - state.cost_basis.get(sym, Decimal("0")))
            for sym, qty in state.positions.items()
        )
        return PortfolioMetrics(
            as_of=state.as_of,
            total_equity=total_equity,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=Decimal("0"),
            total_fees_paid=Decimal("0"),
            max_drawdown_pct=Decimal("0"),
        )
