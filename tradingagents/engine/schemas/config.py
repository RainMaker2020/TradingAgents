from __future__ import annotations
from decimal import Decimal
from tradingagents.engine.schemas.base import BaseSchema
from tradingagents.engine.schemas.orders import FillModel


class SimulationConfig(BaseSchema):
    initial_cash: Decimal
    fill_model: FillModel = FillModel.NEXT_OPEN
    slippage_bps: Decimal = Decimal("5")         # basis points on fill price
    fee_per_trade: Decimal = Decimal("1.0")      # flat cash fee per trade
    fee_bps: Decimal | None = None               # optional % fee on notional
    # Fee policy: ADDITIVE.
    #   total_fee = fee_per_trade + (qty × price × fee_bps / 10000)  [if fee_bps set]
    max_position_pct: Decimal = Decimal("0.10")  # max fraction of equity per symbol
    min_confidence_threshold: float = 0.5        # not enforced by engine internals; apply in RiskManager.evaluate
    random_seed: int = 42                        # reserved for future stochastic components; current slippage arithmetic is deterministic
    calendar_timezone: str = "America/New_York"  # IANA timezone for MarketCalendar
