# tradingagents/engine/runtime/risk_manager.py
"""Concrete RiskManager: enforces cash constraints and confidence threshold."""
from __future__ import annotations
from decimal import Decimal
from typing import Union

from tradingagents.engine.contracts.risk import RiskManager
from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.orders import (
    ApprovedOrder, FillModel, Order, RejectionCode, RejectionReason,
)
from tradingagents.engine.schemas.portfolio import PortfolioState
from tradingagents.engine.schemas.signals import Signal, SignalDirection
import uuid


class ConcreteRiskManager(RiskManager):
    """Default RiskManager for backtesting and paper trading.

    Evaluation steps (in order):
    1. Reject signals below min_confidence_threshold (RISK_THRESHOLD_BREACHED).
    1b. For BUY only: if ``config.max_drawdown_limit`` is set and
        ``peak_equity_for_drawdown`` is provided, reject when current equity
        has fallen more than that fraction below peak (DRAWDOWN_LIMIT_BREACHED).
    2. For SELL: reject if no existing position (EXCEEDS_POSITION_LIMIT — no shares to sell).
    3. Size position via compute_position_size (equity × pct × confidence / price).
    4. Cap qty to what available cash can cover (INSUFFICIENT_CASH if none left).
    5. Cap qty so the total position does not exceed max_position_pct of equity (EXCEEDS_POSITION_LIMIT).
    5b. For BUY only: if ``config.max_position_size`` is set, cap additional shares so
        total position does not exceed that share count (EXCEEDS_POSITION_LIMIT).
    6. Emit ApprovedOrder.

    Order IDs use a per-instance counter (uuid.UUID(int=counter)) rather than
    uuid.uuid4(), so the same sequence of evaluate() calls produces the same
    order IDs across runs. The counter always starts at 0 for a new instance —
    it is NOT wired to SimulationConfig.random_seed, which is reserved for
    future stochastic components (e.g. partial fills, price noise).
    """

    def __init__(self) -> None:
        self._order_counter: int = 0

    def evaluate(
        self,
        signal: Signal,
        portfolio: PortfolioState,
        current_prices: dict[str, Decimal],
        config: SimulationConfig,
        *,
        peak_equity_for_drawdown: Decimal | None = None,
    ) -> Union[ApprovedOrder, RejectionReason]:
        # 1. Confidence gate
        if signal.confidence < config.min_confidence_threshold:
            return RejectionReason(
                code=RejectionCode.RISK_THRESHOLD_BREACHED,
                detail=f"confidence {signal.confidence:.2f} < threshold {config.min_confidence_threshold:.2f}",
            )

        # 1b. Drawdown gate (new BUY only): block entries when equity is too far below peak.
        if (
            signal.direction == SignalDirection.BUY
            and config.max_drawdown_limit is not None
            and peak_equity_for_drawdown is not None
            and peak_equity_for_drawdown > Decimal("0")
        ):
            position_value = sum(
                held * current_prices.get(sym, Decimal("0"))
                for sym, held in portfolio.positions.items()
            )
            equity = portfolio.cash + position_value
            dd = (peak_equity_for_drawdown - equity) / peak_equity_for_drawdown
            if dd > config.max_drawdown_limit:
                return RejectionReason(
                    code=RejectionCode.DRAWDOWN_LIMIT_BREACHED,
                    detail=(
                        f"drawdown {dd:.4f} exceeds limit {config.max_drawdown_limit} "
                        f"(peak_equity={peak_equity_for_drawdown}, equity={equity})"
                    ),
                )

        # 2. SELL guard: reject if no position exists to sell (prevents phantom shorts)
        if signal.direction == SignalDirection.SELL:
            existing_qty = portfolio.positions.get(signal.symbol, Decimal("0"))
            if existing_qty <= Decimal("0"):
                return RejectionReason(
                    code=RejectionCode.EXCEEDS_POSITION_LIMIT,
                    detail=f"no position in {signal.symbol} to sell",
                )

        # 3. Compute target share count from dollar notional
        dollar_notional = self.compute_position_size(signal, portfolio, current_prices, config)
        price = current_prices.get(signal.symbol, Decimal("0"))
        if price <= Decimal("0"):
            return RejectionReason(
                code=RejectionCode.INSUFFICIENT_CASH,
                detail=f"no price available for {signal.symbol}",
            )
        qty = (dollar_notional / price).quantize(Decimal("0.000001"))

        if signal.direction == SignalDirection.SELL:
            # 4-SELL. Cap to existing position — selling generates cash so no affordability check.
            existing_qty = portfolio.positions.get(signal.symbol, Decimal("0"))
            qty = min(qty, existing_qty)
        else:
            # 4-BUY. Cap to affordable shares (prevents negative cash / implicit margin).
            # When fee_bps is set, the actual fill cost is qty×price×(1 + fee_bps/10000) + fee_per_trade.
            # Solve for max qty: spendable = qty × effective_price, where
            # effective_price = price × (1 + fee_bps/10000).
            spendable = portfolio.cash - config.fee_per_trade
            if spendable <= Decimal("0"):
                return RejectionReason(
                    code=RejectionCode.INSUFFICIENT_CASH,
                    detail="cash exhausted",
                )
            if config.fee_bps is not None:
                effective_price = price * (1 + config.fee_bps / Decimal("10000"))
            else:
                effective_price = price
            max_shares = (spendable / effective_price).quantize(Decimal("0.000001"))
            qty = min(qty, max_shares)

            # 5-BUY. Cap to position limit: total holding must not exceed max_position_pct of equity
            position_value = sum(
                held * current_prices.get(sym, Decimal("0"))
                for sym, held in portfolio.positions.items()
            )
            total_equity = portfolio.cash + position_value
            max_allowed_value = config.max_position_pct * total_equity
            current_symbol_value = portfolio.positions.get(signal.symbol, Decimal("0")) * price
            headroom = max_allowed_value - current_symbol_value
            if headroom <= Decimal("0"):
                return RejectionReason(
                    code=RejectionCode.EXCEEDS_POSITION_LIMIT,
                    detail=f"{signal.symbol} already at or above max_position_pct ({config.max_position_pct})",
                )
            qty = min(qty, (headroom / price).quantize(Decimal("0.000001")))

            # 5b-BUY. Optional absolute max shares per symbol (total position cap).
            if config.max_position_size is not None:
                current_shares = portfolio.positions.get(signal.symbol, Decimal("0"))
                room = config.max_position_size - current_shares
                if room <= Decimal("0"):
                    return RejectionReason(
                        code=RejectionCode.EXCEEDS_POSITION_LIMIT,
                        detail=(
                            f"{signal.symbol} at or above max_position_size "
                            f"({config.max_position_size} shares)"
                        ),
                    )
                qty = min(qty, room)

        if qty <= Decimal("0"):
            if signal.direction == SignalDirection.SELL:
                return RejectionReason(
                    code=RejectionCode.EXCEEDS_POSITION_LIMIT,
                    detail="computed sell quantity is zero after position cap",
                )
            return RejectionReason(
                code=RejectionCode.INSUFFICIENT_CASH,
                detail="computed position size is zero after cash cap",
            )

        order_id = uuid.UUID(int=self._order_counter)
        self._order_counter += 1
        order = Order(
            id=order_id,
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=qty,
            created_at=signal.generated_at,
            fill_model=config.fill_model,
            signal_ref=None,
        )
        return ApprovedOrder(
            order=order,
            approved_at=signal.generated_at,
            approved_quantity=qty,
        )
