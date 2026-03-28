# tests/api/test_execution_mode.py
"""Tests for the execution selection layer in RunService.

BacktestLoop and TradingAgentsGraph are mocked so no CSV data or LLM
calls are required.  These tests verify:
  - mode field is stored on RunConfig
  - _run_pipeline dispatches to the correct sub-pipeline
  - Both paths receive the same normalized SimulationConfig (sim_cfg)
  - The backtest path passes sim_cfg to BacktestLoop
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch, call
import threading

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.models.run import RunConfig, SimulationConfigSchema
from api.services.run_service import RunService
from api.store.shared import store as _shared_store


# ---------------------------------------------------------------------------
# RunConfig: mode field
# ---------------------------------------------------------------------------


class TestRunConfigMode:
    def test_default_mode_is_graph(self):
        cfg = RunConfig(ticker="AAPL", date="2024-01-02")
        assert cfg.mode == "graph"

    def test_backtest_mode_accepted(self):
        cfg = RunConfig(ticker="AAPL", date="2024-01-02", mode="backtest")
        assert cfg.mode == "backtest"

    def test_end_date_defaults_to_none(self):
        cfg = RunConfig(ticker="AAPL", date="2024-01-02")
        assert cfg.end_date is None

    def test_end_date_accepted(self):
        cfg = RunConfig(ticker="AAPL", date="2024-01-02", mode="backtest", end_date="2024-12-31")
        assert cfg.end_date == "2024-12-31"

    @pytest.mark.asyncio
    async def test_api_accepts_graph_mode(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/runs", json={
                "ticker": "AAPL", "date": "2024-01-02", "mode": "graph"
            })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_api_accepts_backtest_mode(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/runs", json={
                "ticker": "AAPL", "date": "2024-01-02", "mode": "backtest",
                "end_date": "2024-01-31",
            })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_api_rejects_invalid_mode(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/runs", json={
                "ticker": "AAPL", "date": "2024-01-02", "mode": "invalid_mode"
            })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Dispatcher: routes to correct sub-pipeline
# ---------------------------------------------------------------------------


class TestDispatcher:
    def _svc(self):
        return RunService(_shared_store)

    def _cancel(self):
        return threading.Event()

    def test_graph_mode_calls_run_graph_pipeline(self):
        svc = self._svc()
        config = RunConfig(ticker="AAPL", date="2024-01-02", mode="graph")
        cancel = self._cancel()

        with patch.object(svc, "_run_graph_pipeline") as mock_graph, \
             patch.object(svc, "_run_backtest_pipeline") as mock_backtest:
            svc._run_pipeline("run-001", config, cancel)

        mock_graph.assert_called_once()
        mock_backtest.assert_not_called()

    def test_backtest_mode_calls_run_backtest_pipeline(self):
        svc = self._svc()
        config = RunConfig(ticker="AAPL", date="2024-01-02", mode="backtest")
        cancel = self._cancel()

        with patch.object(svc, "_run_graph_pipeline") as mock_graph, \
             patch.object(svc, "_run_backtest_pipeline") as mock_backtest:
            svc._run_pipeline("run-002", config, cancel)

        mock_backtest.assert_called_once()
        mock_graph.assert_not_called()

    def test_both_paths_receive_same_sim_cfg(self):
        """sim_cfg is computed once in _run_pipeline and passed to both sub-pipelines."""
        svc = self._svc()
        cancel = self._cancel()
        captured: list = []

        def capture_sim_cfg(run_id, config, sim_cfg, cancel_event):
            captured.append(sim_cfg)

        # Test graph path
        config_graph = RunConfig(
            ticker="AAPL", date="2024-01-02", mode="graph",
            simulation_config={"initial_cash": 75000, "max_position_pct": 15},
        )
        with patch.object(svc, "_run_graph_pipeline", side_effect=capture_sim_cfg):
            svc._run_pipeline("run-003", config_graph, cancel)

        assert len(captured) == 1
        assert captured[0].initial_cash == Decimal("75000")
        assert captured[0].max_position_pct == Decimal("0.15")   # percent → ratio

        # Test backtest path — same input, same normalized output
        config_backtest = RunConfig(
            ticker="AAPL", date="2024-01-02", mode="backtest",
            simulation_config={"initial_cash": 75000, "max_position_pct": 15},
        )
        with patch.object(svc, "_run_backtest_pipeline", side_effect=capture_sim_cfg):
            svc._run_pipeline("run-004", config_backtest, cancel)

        assert len(captured) == 2
        assert captured[1].initial_cash == captured[0].initial_cash
        assert captured[1].max_position_pct == captured[0].max_position_pct


# ---------------------------------------------------------------------------
# Backtest path: sim_cfg consumed by BacktestLoop
# ---------------------------------------------------------------------------


class TestBacktestPathConsumesSimCfg:
    """Verify BacktestLoop receives the normalized sim_cfg, not raw percent values."""

    def _svc(self):
        return RunService(_shared_store)

    def test_backtest_loop_receives_normalized_sim_cfg(self):
        svc = self._svc()
        cancel = threading.Event()

        config = RunConfig(
            ticker="AAPL",
            date="2024-01-02",
            mode="backtest",
            simulation_config={
                "initial_cash": 50000,
                "max_position_pct": 20,   # percent input
                "slippage_bps": 3,
            },
        )

        # Expected normalized values (ratio, not percent)
        expected_cash = Decimal("50000")
        expected_max_pos = Decimal("0.20")   # 20% → 0.20

        captured_cfg = []

        # Fake BacktestLoop that records the config it receives
        class FakeBacktestLoop:
            def __init__(self, feed, strategy, risk, simulator, portfolio, config):
                captured_cfg.append(config)

            def run(self, ticker, start, end):
                from tradingagents.engine.schemas.portfolio import (
                    BacktestResult, BacktestEventType, PortfolioState, PortfolioMetrics,
                )
                from datetime import date as _date, datetime, timezone
                from decimal import Decimal
                now = datetime(2024, 1, 2, tzinfo=timezone.utc)
                state = PortfolioState(
                    as_of=now, cash=Decimal("50000"), positions={}, cost_basis={}
                )
                metrics = PortfolioMetrics(
                    as_of=now,
                    total_equity=Decimal("50000"),
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    total_fees_paid=Decimal("0"),
                    max_drawdown_pct=None,
                )
                return BacktestResult(
                    symbol="AAPL",
                    start=_date(2024, 1, 2),
                    end=_date(2024, 1, 2),
                    initial_state=state,
                    final_state=state,
                    events=(),
                    metrics=metrics,
                )

        fake_run_id = "run-test-backtest"

        # Call _run_backtest_pipeline directly with a mocked BacktestLoop
        sim_cfg = svc._normalize_sim_config(config)

        with patch("api.services.run_service.BacktestLoop", FakeBacktestLoop), \
             patch("tradingagents.engine.adapters.csv_feed.CsvDataFeed") as mock_feed, \
             patch("tradingagents.engine.adapters.langgraph_strategy.LangGraphStrategyAdapter") as mock_strategy:
            # CsvDataFeed raises FileNotFoundError by default; make it succeed
            mock_feed.return_value = MagicMock()
            mock_strategy.return_value = MagicMock(close=MagicMock())
            svc._run_backtest_pipeline(fake_run_id, config, sim_cfg, cancel)

        assert len(captured_cfg) == 1
        cfg_received = captured_cfg[0]
        assert cfg_received.initial_cash == expected_cash
        assert cfg_received.max_position_pct == expected_max_pos   # ratio, not percent
        assert cfg_received.slippage_bps == Decimal("3")
        strategy_kwargs = mock_strategy.call_args.kwargs
        assert "should_cancel" in strategy_kwargs
        assert callable(strategy_kwargs["should_cancel"])

    def test_backtest_path_errors_gracefully_on_missing_csv(self):
        """FileNotFoundError from CsvDataFeed writes error to store, not a crash."""
        svc = self._svc()
        cancel = threading.Event()

        run = _shared_store.create(RunConfig(ticker="MISSING_TICKER", date="2024-01-02"))
        config = RunConfig(ticker="MISSING_TICKER", date="2024-01-02", mode="backtest")
        sim_cfg = svc._normalize_sim_config(config)
        # _run_backtest_pipeline writes errors via try_error_run (RUNNING -> ERROR),
        # so the run must be claimed first to mirror real stream_events flow.
        assert _shared_store.try_claim_run(run.id) is True

        with patch("tradingagents.engine.adapters.csv_feed.CsvDataFeed",
                   side_effect=FileNotFoundError("no CSV for MISSING_TICKER")):
            svc._run_backtest_pipeline(run.id, config, sim_cfg, cancel)

        updated = _shared_store.get(run.id)
        assert updated.error is not None
        assert "MISSING_TICKER" in (updated.error or "")
