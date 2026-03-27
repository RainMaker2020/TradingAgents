# tests/api/test_simulation_config.py
"""API tests for simulation_config field on run-creation endpoint."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.models.run import RunConfig, SimulationConfigSchema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_PAYLOAD = {"ticker": "AAPL", "date": "2024-01-02"}


async def _create_run(client: AsyncClient, extra: dict | None = None) -> dict:
    payload = {**_BASE_PAYLOAD, **(extra or {})}
    resp = await client.post("/api/runs", json=payload)
    return resp


# ---------------------------------------------------------------------------
# Backward compatibility: simulation_config is optional
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    @pytest.mark.asyncio
    async def test_omitting_simulation_config_creates_run(self):
        """Existing clients that don't send simulation_config must continue to work."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client)
        assert resp.status_code == 200
        assert "id" in resp.json()

    @pytest.mark.asyncio
    async def test_omitting_simulation_config_uses_defaults(self):
        """When simulation_config is absent, RunConfig.simulation_config is None."""
        config = RunConfig(ticker="AAPL", date="2024-01-02")
        assert config.simulation_config is None

    def test_simulation_config_schema_defaults(self):
        """Default SimulationConfigSchema matches engine defaults."""
        schema = SimulationConfigSchema()
        assert schema.initial_cash == 100_000
        assert schema.slippage_bps == 5
        assert schema.fee_per_trade == 1.0
        assert schema.fee_bps is None
        assert schema.max_position_pct == 10       # percent, not ratio
        assert schema.fill_model == "NEXT_OPEN"
        assert schema.min_confidence_threshold == 0.5
        assert schema.random_seed == 42
        assert schema.calendar_timezone == "America/New_York"


# ---------------------------------------------------------------------------
# Custom config accepted and stored
# ---------------------------------------------------------------------------


class TestCustomConfig:
    @pytest.mark.asyncio
    async def test_custom_simulation_config_accepted(self):
        """POST with simulation_config object returns 200."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {
                "simulation_config": {
                    "initial_cash": 50000,
                    "slippage_bps": 3,
                    "fee_per_trade": 0.5,
                    "max_position_pct": 20,
                }
            })
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_custom_values_stored_in_run_config(self):
        """Custom simulation_config values are stored on RunConfig."""
        config = RunConfig(
            ticker="AAPL",
            date="2024-01-02",
            simulation_config={
                "initial_cash": 50000,
                "max_position_pct": 20,
            },
        )
        assert config.simulation_config is not None
        assert config.simulation_config.initial_cash == 50_000
        assert config.simulation_config.max_position_pct == 20   # stored as percent

    def test_max_position_pct_stored_as_percent(self):
        """API stores percent (10); engine normalization happens in service layer."""
        cfg = SimulationConfigSchema(max_position_pct=10)
        assert cfg.max_position_pct == 10   # NOT 0.10 — percent at API boundary


# ---------------------------------------------------------------------------
# Normalization: percent → ratio
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_service_layer_normalizes_max_position_pct(self):
        """SimulationConfigInput converts percent input to ratio for engine."""
        from tradingagents.engine.schemas.config_input import SimulationConfigInput

        schema = SimulationConfigSchema(max_position_pct=10)
        sim_cfg = SimulationConfigInput(
            **schema.model_dump(exclude_none=True)
        ).to_simulation_config()

        from decimal import Decimal
        assert sim_cfg.max_position_pct == Decimal("0.10")

    def test_25_percent_normalizes_to_0_25(self):
        from tradingagents.engine.schemas.config_input import SimulationConfigInput
        from decimal import Decimal

        schema = SimulationConfigSchema(max_position_pct=25)
        sim_cfg = SimulationConfigInput(**schema.model_dump(exclude_none=True)).to_simulation_config()
        assert sim_cfg.max_position_pct == Decimal("0.25")

    def test_defaults_normalize_correctly(self):
        """Default schema (10%) normalizes to 0.10 in engine config."""
        from tradingagents.engine.schemas.config_input import SimulationConfigInput
        from decimal import Decimal

        schema = SimulationConfigSchema()
        sim_cfg = SimulationConfigInput(**schema.model_dump(exclude_none=True)).to_simulation_config()
        assert sim_cfg.max_position_pct == Decimal("0.10")
        assert sim_cfg.initial_cash == Decimal("100000")


# ---------------------------------------------------------------------------
# Passthrough fields
# ---------------------------------------------------------------------------


class TestPassthroughFields:
    def test_fill_model_passthrough(self):
        from tradingagents.engine.schemas.config_input import SimulationConfigInput
        from tradingagents.engine.schemas.orders import FillModel

        schema = SimulationConfigSchema(fill_model="NEXT_OPEN")
        sim_cfg = SimulationConfigInput(**schema.model_dump(exclude_none=True)).to_simulation_config()
        assert sim_cfg.fill_model == FillModel.NEXT_OPEN

    def test_random_seed_passthrough(self):
        from tradingagents.engine.schemas.config_input import SimulationConfigInput

        schema = SimulationConfigSchema(random_seed=99)
        sim_cfg = SimulationConfigInput(**schema.model_dump(exclude_none=True)).to_simulation_config()
        assert sim_cfg.random_seed == 99

    def test_calendar_timezone_passthrough(self):
        from tradingagents.engine.schemas.config_input import SimulationConfigInput

        schema = SimulationConfigSchema(calendar_timezone="UTC")
        sim_cfg = SimulationConfigInput(**schema.model_dump(exclude_none=True)).to_simulation_config()
        assert sim_cfg.calendar_timezone == "UTC"

    def test_min_confidence_threshold_passthrough(self):
        from tradingagents.engine.schemas.config_input import SimulationConfigInput

        schema = SimulationConfigSchema(min_confidence_threshold=0.7)
        sim_cfg = SimulationConfigInput(**schema.model_dump(exclude_none=True)).to_simulation_config()
        assert sim_cfg.min_confidence_threshold == 0.7

    def test_fee_bps_passthrough(self):
        from tradingagents.engine.schemas.config_input import SimulationConfigInput
        from decimal import Decimal

        schema = SimulationConfigSchema(fee_bps=3.0)
        sim_cfg = SimulationConfigInput(**schema.model_dump(exclude_none=True)).to_simulation_config()
        assert sim_cfg.fee_bps == Decimal("3.0")

    def test_fee_bps_none_passthrough(self):
        from tradingagents.engine.schemas.config_input import SimulationConfigInput

        schema = SimulationConfigSchema(fee_bps=None)
        sim_cfg = SimulationConfigInput(**schema.model_dump(exclude_none=True)).to_simulation_config()
        assert sim_cfg.fee_bps is None


# ---------------------------------------------------------------------------
# Validation: invalid values must return 422
# ---------------------------------------------------------------------------


class TestValidation422:
    @pytest.mark.asyncio
    async def test_non_positive_cash_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"initial_cash": 0}})
        assert resp.status_code == 422
        body = resp.json()
        assert any("initial_cash" in str(e.get("loc", "")) for e in body.get("detail", []))

    @pytest.mark.asyncio
    async def test_negative_cash_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"initial_cash": -1000}})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_slippage_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"slippage_bps": -1}})
        assert resp.status_code == 422
        body = resp.json()
        assert any("slippage_bps" in str(e.get("loc", "")) for e in body.get("detail", []))

    @pytest.mark.asyncio
    async def test_negative_fee_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"fee_per_trade": -0.01}})
        assert resp.status_code == 422
        body = resp.json()
        assert any("fee_per_trade" in str(e.get("loc", "")) for e in body.get("detail", []))

    @pytest.mark.asyncio
    async def test_max_position_zero_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"max_position_pct": 0}})
        assert resp.status_code == 422
        body = resp.json()
        assert any("max_position_pct" in str(e.get("loc", "")) for e in body.get("detail", []))

    @pytest.mark.asyncio
    async def test_max_position_over_100_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"max_position_pct": 101}})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_non_numeric_cash_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"initial_cash": "not_a_number"}})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_fee_bps_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"fee_bps": -1}})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_fill_model_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"fill_model": "INVALID_MODEL"}})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_confidence_threshold_out_of_range_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await _create_run(client, {"simulation_config": {"min_confidence_threshold": 1.5}})
        assert resp.status_code == 422
