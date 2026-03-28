# tests/engine/test_config_input.py
"""Unit tests for SimulationConfigInput DTO."""
from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.config_input import SimulationConfigInput
from tradingagents.engine.schemas.orders import FillModel


class TestDefaults:
    def test_default_values(self):
        inp = SimulationConfigInput()
        assert inp.initial_cash == Decimal("100000")
        assert inp.slippage_bps == Decimal("5")
        assert inp.fee_per_trade == Decimal("1.0")
        assert inp.max_position_pct == Decimal("10")

    def test_to_simulation_config_returns_correct_type(self):
        cfg = SimulationConfigInput().to_simulation_config()
        assert isinstance(cfg, SimulationConfig)

    def test_to_simulation_config_defaults_passthrough(self):
        cfg = SimulationConfigInput().to_simulation_config()
        assert cfg.initial_cash == Decimal("100000")
        assert cfg.slippage_bps == Decimal("5")
        assert cfg.fee_per_trade == Decimal("1.0")
        assert cfg.fee_bps is None
        assert cfg.fill_model == FillModel.NEXT_OPEN
        assert cfg.min_confidence_threshold == 0.5
        assert cfg.random_seed == 42
        assert cfg.calendar_timezone == "America/New_York"

    def test_to_simulation_config_max_position_normalized(self):
        """Default 10% must become 0.10 ratio in engine config."""
        cfg = SimulationConfigInput().to_simulation_config()
        assert cfg.max_position_pct == Decimal("0.10")


class TestNormalization:
    """max_position_pct: percent → ratio conversion."""

    def test_10_percent_becomes_0_10(self):
        cfg = SimulationConfigInput(max_position_pct=10).to_simulation_config()
        assert cfg.max_position_pct == Decimal("0.10")

    def test_25_percent_becomes_0_25(self):
        cfg = SimulationConfigInput(max_position_pct=25).to_simulation_config()
        assert cfg.max_position_pct == Decimal("0.25")

    def test_100_percent_becomes_1_0(self):
        cfg = SimulationConfigInput(max_position_pct=100).to_simulation_config()
        assert cfg.max_position_pct == Decimal("1")

    def test_1_percent_becomes_0_01(self):
        cfg = SimulationConfigInput(max_position_pct=1).to_simulation_config()
        assert cfg.max_position_pct == Decimal("0.01")

    def test_engine_max_position_pct_is_always_lte_1(self):
        for pct in [1, 5, 10, 25, 50, 100]:
            cfg = SimulationConfigInput(max_position_pct=pct).to_simulation_config()
            assert Decimal("0") < cfg.max_position_pct <= Decimal("1"), (
                f"max_position_pct={pct}% → engine ratio {cfg.max_position_pct} is out of range"
            )


class TestDecimalParsing:
    """Numeric inputs survive float/str/int boundaries without precision loss."""

    def test_float_initial_cash_parsed_as_decimal(self):
        inp = SimulationConfigInput(initial_cash=100000.0)
        assert isinstance(inp.initial_cash, Decimal)
        assert inp.initial_cash == Decimal("100000.0")

    def test_float_slippage_parsed_as_decimal(self):
        inp = SimulationConfigInput(slippage_bps=5.0)
        assert isinstance(inp.slippage_bps, Decimal)

    def test_float_fee_parsed_as_decimal(self):
        inp = SimulationConfigInput(fee_per_trade=1.0)
        assert isinstance(inp.fee_per_trade, Decimal)

    def test_float_max_position_parsed_as_decimal(self):
        inp = SimulationConfigInput(max_position_pct=10.0)
        assert isinstance(inp.max_position_pct, Decimal)

    def test_string_inputs_accepted(self):
        inp = SimulationConfigInput(
            initial_cash="50000",
            slippage_bps="3",
            fee_per_trade="0.5",
            max_position_pct="20",
        )
        assert inp.initial_cash == Decimal("50000")
        assert inp.slippage_bps == Decimal("3")
        assert inp.fee_per_trade == Decimal("0.5")
        assert inp.max_position_pct == Decimal("20")

    def test_integer_inputs_accepted(self):
        inp = SimulationConfigInput(
            initial_cash=50000,
            slippage_bps=3,
            fee_per_trade=0,
            max_position_pct=15,
        )
        assert inp.initial_cash == Decimal("50000")
        assert inp.max_position_pct == Decimal("15")

    def test_decimal_inputs_passthrough(self):
        inp = SimulationConfigInput(
            initial_cash=Decimal("75000"),
            max_position_pct=Decimal("5"),
        )
        assert inp.initial_cash == Decimal("75000")
        assert inp.max_position_pct == Decimal("5")


class TestValidation:
    """All validation rules emit descriptive messages."""

    # initial_cash
    def test_rejects_zero_initial_cash(self):
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfigInput(initial_cash=0)
        assert "Initial Cash" in str(exc_info.value)

    def test_rejects_negative_initial_cash(self):
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfigInput(initial_cash=-1000)
        assert "Initial Cash" in str(exc_info.value)

    # slippage_bps
    def test_rejects_negative_slippage(self):
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfigInput(slippage_bps=-1)
        assert "Slippage" in str(exc_info.value)

    def test_zero_slippage_is_valid(self):
        inp = SimulationConfigInput(slippage_bps=0)
        assert inp.slippage_bps == Decimal("0")

    # fee_per_trade
    def test_rejects_negative_fee(self):
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfigInput(fee_per_trade=-0.01)
        assert "Fee Per Trade" in str(exc_info.value)

    def test_zero_fee_is_valid(self):
        inp = SimulationConfigInput(fee_per_trade=0)
        assert inp.fee_per_trade == Decimal("0")

    # max_position_pct
    def test_rejects_zero_max_position_pct(self):
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfigInput(max_position_pct=0)
        assert "max_position_pct" in str(exc_info.value)

    def test_rejects_negative_max_position_pct(self):
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfigInput(max_position_pct=-5)
        assert "max_position_pct" in str(exc_info.value)

    def test_rejects_max_position_pct_over_100(self):
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfigInput(max_position_pct=101)
        assert "max_position_pct" in str(exc_info.value)

    def test_100_percent_is_valid_upper_bound(self):
        inp = SimulationConfigInput(max_position_pct=100)
        assert inp.max_position_pct == Decimal("100")

    def test_rejects_non_numeric_string(self):
        with pytest.raises(ValidationError):
            SimulationConfigInput(initial_cash="not_a_number")

    def test_rejects_non_numeric_fee(self):
        with pytest.raises(ValidationError):
            SimulationConfigInput(fee_per_trade="free")

    # fee_bps
    def test_fee_bps_none_by_default(self):
        inp = SimulationConfigInput()
        assert inp.fee_bps is None

    def test_fee_bps_accepted_as_decimal(self):
        inp = SimulationConfigInput(fee_bps=2)
        assert inp.fee_bps == Decimal("2")

    def test_fee_bps_zero_is_valid(self):
        inp = SimulationConfigInput(fee_bps=0)
        assert inp.fee_bps == Decimal("0")

    def test_rejects_negative_fee_bps(self):
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfigInput(fee_bps=-1)
        assert "bps" in str(exc_info.value)


class TestPassthroughFields:
    """Engine pass-through fields survive the DTO boundary unchanged."""

    def test_fill_model_passthrough(self):
        from tradingagents.engine.schemas.orders import FillModel
        cfg = SimulationConfigInput(fill_model=FillModel.NEXT_OPEN).to_simulation_config()
        assert cfg.fill_model == FillModel.NEXT_OPEN

    def test_min_confidence_threshold_passthrough(self):
        cfg = SimulationConfigInput(min_confidence_threshold=0.7).to_simulation_config()
        assert cfg.min_confidence_threshold == 0.7

    def test_random_seed_passthrough(self):
        cfg = SimulationConfigInput(random_seed=99).to_simulation_config()
        assert cfg.random_seed == 99

    def test_calendar_timezone_passthrough(self):
        cfg = SimulationConfigInput(calendar_timezone="UTC").to_simulation_config()
        assert cfg.calendar_timezone == "UTC"

    def test_fee_bps_none_passthrough(self):
        cfg = SimulationConfigInput(fee_bps=None).to_simulation_config()
        assert cfg.fee_bps is None

    def test_fee_bps_value_passthrough(self):
        cfg = SimulationConfigInput(fee_bps=3).to_simulation_config()
        assert cfg.fee_bps == Decimal("3")


class TestApiPayloadShape:
    """Validates the documented JSON payload shape round-trips correctly."""

    def test_typical_api_payload(self):
        """Simulate JSON.parse → dict → SimulationConfigInput → SimulationConfig."""
        payload = {
            "initial_cash": 100000,
            "slippage_bps": 5,
            "fee_per_trade": 1.0,
            "max_position_pct": 10,
        }
        inp = SimulationConfigInput(**payload)
        cfg = inp.to_simulation_config()

        assert cfg.initial_cash == Decimal("100000")
        assert cfg.slippage_bps == Decimal("5")
        assert cfg.fee_per_trade == Decimal("1.0")
        assert cfg.max_position_pct == Decimal("0.10")

    def test_fractional_percent_in_payload(self):
        """API may send 2.5 for 2.5%; ensure conversion is exact."""
        payload = {"initial_cash": 50000, "max_position_pct": 2.5}
        cfg = SimulationConfigInput(**payload).to_simulation_config()
        assert cfg.max_position_pct == Decimal("2.5") / Decimal("100")
