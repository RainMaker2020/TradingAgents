from __future__ import annotations
from decimal import Decimal
from tradingagents.engine.contracts.portfolio import Portfolio
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.orders import FillResult
from tradingagents.engine.schemas.portfolio import PortfolioMetrics, PortfolioState
from tradingagents.engine.schemas.signals import SignalDirection


class InMemoryPortfolio(Portfolio):
    """Pure in-memory portfolio. All state transitions return new PortfolioState objects.
    v1: long-only (no short positions). Positions floor at zero on SELL.
    """

    def apply_fill(self, state: PortfolioState, fill: FillResult) -> PortfolioState:
        positions = dict(state.positions)
        cost_basis = dict(state.cost_basis)
        cash = state.cash
        notional = fill.filled_quantity * fill.fill_price

        if fill.direction == SignalDirection.BUY:
            current_qty = positions.get(fill.symbol, Decimal("0"))
            current_cb = cost_basis.get(fill.symbol, Decimal("0"))
            new_qty = current_qty + fill.filled_quantity
            # weighted average cost basis
            total_cost = current_qty * current_cb + notional
            cost_basis[fill.symbol] = (total_cost / new_qty).quantize(Decimal("0.0001"))
            positions[fill.symbol] = new_qty
            cash = cash - notional - fill.fees
        else:  # SELL
            current_qty = positions.get(fill.symbol, Decimal("0"))
            new_qty = max(Decimal("0"), current_qty - fill.filled_quantity)
            if new_qty == Decimal("0"):
                positions.pop(fill.symbol, None)
                cost_basis.pop(fill.symbol, None)
            else:
                positions[fill.symbol] = new_qty
            cash = cash + notional - fill.fees

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
            qty * (prices.get(sym, state.cost_basis.get(sym, Decimal("0"))) - state.cost_basis.get(sym, Decimal("0")))
            for sym, qty in state.positions.items()
        )
        return PortfolioMetrics(
            as_of=state.as_of,
            total_equity=total_equity,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=Decimal("0"),   # v1: realized PnL tracking deferred
            total_fees_paid=Decimal("0"), # v1: fee tracking deferred
            max_drawdown_pct=Decimal("0"), # v1: drawdown tracking deferred
        )
