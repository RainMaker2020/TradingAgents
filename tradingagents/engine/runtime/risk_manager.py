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
    2. For SELL: reject if no existing position (EXCEEDS_POSITION_LIMIT — no shares to sell).
    3. Size position via compute_position_size (equity × pct × confidence / price).
    4. Cap qty to what available cash can cover (INSUFFICIENT_CASH if none left).
    5. Cap qty so the total position does not exceed max_position_pct of equity (EXCEEDS_POSITION_LIMIT).
    6. Emit ApprovedOrder.
    """

    def evaluate(
        self,
        signal: Signal,
        portfolio: PortfolioState,
        current_prices: dict[str, Decimal],
        config: SimulationConfig,
    ) -> Union[ApprovedOrder, RejectionReason]:
        # 1. Confidence gate
        if signal.confidence < config.min_confidence_threshold:
            return RejectionReason(
                code=RejectionCode.RISK_THRESHOLD_BREACHED,
                detail=f"confidence {signal.confidence:.2f} < threshold {config.min_confidence_threshold:.2f}",
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
            # 4-BUY. Cap to affordable shares (prevents negative cash / implicit margin)
            spendable = portfolio.cash - config.fee_per_trade
            if spendable <= Decimal("0"):
                return RejectionReason(
                    code=RejectionCode.INSUFFICIENT_CASH,
                    detail="cash exhausted",
                )
            max_shares = (spendable / price).quantize(Decimal("0.000001"))
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

        order = Order(
            id=uuid.uuid4(),
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
