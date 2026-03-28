# tradingagents/engine/schemas/config_input.py
"""User-facing SimulationConfig input DTO.

Accepts friendly units and normalizes to engine units before constructing
SimulationConfig.  Use this at ALL external boundaries (API, CLI, UI) — never
construct SimulationConfig directly from raw user input.

Unit conventions
----------------
Field               User input          Engine unit
------------------  ------------------  -----------
initial_cash        USD  e.g. 100000    Decimal USD
slippage_bps        bps  e.g. 5         Decimal bps
fee_per_trade       USD  e.g. 1.0       Decimal USD
fee_bps             bps  e.g. None      Decimal bps  (optional additive % fee)
max_position_pct    %    e.g. 10        Decimal ratio (10 → 0.10)
stop_loss_percentage   % optional e.g. 5   Decimal ratio (5 → 0.05), None = off
take_profit_target  % optional e.g. 10    Decimal ratio (10 → 0.10), None = off
max_drawdown_limit  % optional e.g. 15   Decimal ratio (15 → 0.15), None = off
max_position_size   shares e.g. 500      Decimal share cap, None = no cap
fill_model          FillModel enum      passthrough
min_confidence_threshold  float 0-1     passthrough
random_seed         int                 passthrough
calendar_timezone   IANA string         passthrough

The critical conversion: max_position_pct percent → ratio (divide by 100).
Keeping these two representations separate at the boundary prevents the
common off-by-100x bug where engine receives 10 and treats it as 1000% equity.

Note on BaseModel vs BaseSchema
--------------------------------
SimulationConfigInput deliberately inherits from plain ``BaseModel``, not the
project's ``BaseSchema``.  ``BaseSchema`` enforces ``frozen=True`` (immutable
value objects) and UTC-awareness for datetimes — semantics appropriate for
engine value objects but not for an ephemeral input DTO that is constructed,
validated once, and immediately consumed.  This is an intentional deviation.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator

from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.orders import FillModel


class SimulationConfigInput(BaseModel):
    """User-facing input schema for simulation configuration.

    Numeric fields are parsed via ``Decimal(str(v))`` to avoid float precision
    loss at the JSON/HTTP boundary.

    ``max_position_pct`` is expressed as a **percent** (0 < value ≤ 100) and is
    divided by 100 when passed to ``SimulationConfig`` (which expects a ratio).

    All other ``SimulationConfig`` fields are accepted as-is with their engine
    defaults, so callers can override any field without bypassing this DTO.

    Validation rules (user-facing fields)
    --------------------------------------
    - initial_cash              > 0
    - slippage_bps              >= 0
    - fee_per_trade             >= 0
    - fee_bps                   >= 0  (when provided)
    - 0 < max_position_pct <= 100     (user-facing percent)
    - optional risk percents: 0 < value <= 100 when set
    - optional max_position_size: > 0 when set (share count)
    """

    # ── User-facing fields (with unit labels) ──────────────────────────────
    initial_cash: Decimal = Field(
        default=Decimal("100000"),
        description="Starting portfolio cash in USD. Must be greater than 0.",
    )
    slippage_bps: Decimal = Field(
        default=Decimal("5"),
        description="Slippage applied to each fill price, in basis points (bps). Must be 0 or greater.",
    )
    fee_per_trade: Decimal = Field(
        default=Decimal("1.0"),
        description="Flat fee in USD charged per trade. Must be 0 or greater.",
    )
    fee_bps: Decimal | None = Field(
        default=None,
        description=(
            "Optional percentage fee on notional, in basis points (bps). "
            "When set: total_fee = fee_per_trade + qty × price × fee_bps / 10000. "
            "Must be 0 or greater when provided."
        ),
    )
    max_position_pct: Decimal = Field(
        default=Decimal("10"),
        description=(
            "Maximum position size as a percent of total equity (e.g. 10 = 10%). "
            "Must be greater than 0 and at most 100."
        ),
    )
    stop_loss_percentage: Decimal | None = Field(
        default=None,
        description=(
            "Stop loss below average entry, as percent (e.g. 5 = 5%). "
            "Normalized to engine ratio. None disables."
        ),
    )
    take_profit_target: Decimal | None = Field(
        default=None,
        description=(
            "Take-profit target above average entry, as percent. "
            "Normalized to engine ratio. None disables."
        ),
    )
    max_drawdown_limit: Decimal | None = Field(
        default=None,
        description=(
            "Max portfolio drawdown from peak equity, as percent (e.g. 15 = 15%). "
            "New BUY signals are blocked when exceeded. None disables."
        ),
    )
    max_position_size: Decimal | None = Field(
        default=None,
        description=(
            "Hard cap on shares held per symbol after a BUY. None = no share cap "
            "(only max_position_pct applies)."
        ),
    )

    # ── Engine pass-through fields (no unit conversion needed) ─────────────
    fill_model: FillModel = Field(
        default=FillModel.NEXT_OPEN,
        description="Fill execution model.",
    )
    min_confidence_threshold: float = Field(
        default=0.5,
        description="Minimum signal confidence to pass the risk gate (0.0–1.0).",
    )
    random_seed: int = Field(
        default=42,
        description="Seed for any stochastic engine components.",
    )
    calendar_timezone: str = Field(
        default="America/New_York",
        description="IANA timezone for the market calendar.",
    )

    model_config = {"arbitrary_types_allowed": True}

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    @field_validator(
        "initial_cash",
        "slippage_bps",
        "fee_per_trade",
        "max_position_pct",
        mode="before",
    )
    @classmethod
    def _parse_decimal(cls, v: Any) -> Decimal:
        """Accept int, float, str, or Decimal. Convert via str to preserve precision."""
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except InvalidOperation:
            raise ValueError("Cannot parse the provided value as a numeric value")

    @field_validator("fee_bps", mode="before")
    @classmethod
    def _parse_optional_decimal_fee_bps(cls, v: Any) -> Decimal | None:
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except InvalidOperation:
            raise ValueError("Cannot parse the provided value as a numeric value")

    @field_validator(
        "stop_loss_percentage",
        "take_profit_target",
        "max_drawdown_limit",
        "max_position_size",
        mode="before",
    )
    @classmethod
    def _parse_optional_risk_decimals(cls, v: Any) -> Decimal | None:
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except InvalidOperation:
            raise ValueError("Cannot parse the provided value as a numeric value")

    # ------------------------------------------------------------------
    # Field-level validators (run after parsing)
    # ------------------------------------------------------------------

    @field_validator("initial_cash")
    @classmethod
    def _initial_cash_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Initial Cash (USD) must be greater than 0")
        return v

    @field_validator("slippage_bps")
    @classmethod
    def _slippage_non_negative(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Slippage (bps) must be 0 or greater")
        return v

    @field_validator("fee_per_trade")
    @classmethod
    def _fee_non_negative(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Fee Per Trade (USD) must be 0 or greater")
        return v

    @field_validator("fee_bps")
    @classmethod
    def _fee_bps_non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < Decimal("0"):
            raise ValueError("Fee (bps) must be 0 or greater when provided")
        return v

    @field_validator("max_position_pct")
    @classmethod
    def _max_position_in_range(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0") or v > Decimal("100"):
            raise ValueError(
                "Max Position Size must be between 0 and 100% "
                "(exclusive lower bound, inclusive upper bound)"
            )
        return v

    @field_validator("stop_loss_percentage", "take_profit_target", "max_drawdown_limit")
    @classmethod
    def _optional_risk_percent(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return None
        if v <= Decimal("0") or v > Decimal("100"):
            raise ValueError("Risk percentage fields must be between 0 and 100% when set")
        return v

    @field_validator("max_position_size")
    @classmethod
    def _optional_max_shares(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return None
        if v <= Decimal("0"):
            raise ValueError("max_position_size must be greater than 0 when set")
        return v

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def to_simulation_config(self) -> SimulationConfig:
        """Return a normalized ``SimulationConfig`` suitable for engine use.

        Conversion applied:
          ``max_position_pct``  percent → ratio  (10 % → 0.10)

        All other fields are passed through unchanged.
        """
        return SimulationConfig(
            initial_cash=self.initial_cash,
            fill_model=self.fill_model,
            slippage_bps=self.slippage_bps,
            fee_per_trade=self.fee_per_trade,
            fee_bps=self.fee_bps,
            max_position_pct=self.max_position_pct / Decimal("100"),
            max_position_size=self.max_position_size,
            stop_loss_pct=(
                self.stop_loss_percentage / Decimal("100")
                if self.stop_loss_percentage is not None
                else None
            ),
            take_profit_pct=(
                self.take_profit_target / Decimal("100")
                if self.take_profit_target is not None
                else None
            ),
            max_drawdown_limit=(
                self.max_drawdown_limit / Decimal("100")
                if self.max_drawdown_limit is not None
                else None
            ),
            min_confidence_threshold=self.min_confidence_threshold,
            random_seed=self.random_seed,
            calendar_timezone=self.calendar_timezone,
        )
