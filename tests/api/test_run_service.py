import pytest
import threading
from collections import defaultdict
from unittest.mock import patch, MagicMock
from decimal import Decimal

from api.services.run_service import RunService, _adapter_confidence_for_risk_gate
from tradingagents.engine.schemas.config import SimulationConfig
from api.store.runs_store import RunsStore
from api.models.run import RunConfig, RunStatus


@pytest.fixture
def store(tmp_path):
    return RunsStore(tmp_path / "test.sqlite")


@pytest.fixture
def service(store):
    return RunService(store)


def test_adapter_confidence_for_risk_gate_matches_threshold_above_floor():
    hi = SimulationConfig(initial_cash=Decimal("1"), min_confidence_threshold=0.95)
    assert _adapter_confidence_for_risk_gate(hi) == 0.95
    lo = SimulationConfig(initial_cash=Decimal("1"), min_confidence_threshold=0.5)
    assert _adapter_confidence_for_risk_gate(lo) == 0.8
    cap = SimulationConfig(initial_cash=Decimal("1"), min_confidence_threshold=1.0)
    assert _adapter_confidence_for_risk_gate(cap) == 1.0


def _mock_graph(stream_yields, decision="BUY"):
    """Return a mock TradingAgentsGraph instance for stream_propagate tests."""
    mock = MagicMock()
    mock.stream_propagate.return_value = iter(stream_yields)
    mock._last_decision = decision
    return mock


def test_emits_agent_start_and_complete_per_step(service, store):
    config = RunConfig(ticker="NVDA", date="2026-03-23")
    run = store.create(config)
    yields = [
        ("market_analyst", "bullish"),
        ("news_analyst", "stable"),
    ]
    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        MockGraph.return_value = _mock_graph(yields)
        events = list(service.stream_events(run.id))

    starts    = [e for e in events if e["event"] == "agent:start"]
    completes = [e for e in events if e["event"] == "agent:complete"]
    assert len(starts) == 2
    assert len(completes) == 2
    assert starts[0]["data"]["step"] == "market_analyst"
    assert starts[0]["data"]["turn"] == 0
    assert completes[0]["data"]["report"] == "bullish"


def test_turn_increments_for_repeat_steps(service, store):
    config = RunConfig(ticker="NVDA", date="2026-03-23")
    run = store.create(config)
    yields = [
        ("bull_researcher", "bull round 1"),
        ("bear_researcher", "bear round 1"),
        ("bull_researcher", "bull round 2"),
    ]
    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        MockGraph.return_value = _mock_graph(yields)
        events = list(service.stream_events(run.id))

    bull_completes = [e for e in events
                      if e["event"] == "agent:complete" and e["data"]["step"] == "bull_researcher"]
    assert len(bull_completes) == 2
    assert bull_completes[0]["data"]["turn"] == 0
    assert bull_completes[1]["data"]["turn"] == 1


def test_run_complete_emitted_with_decision(service, store):
    config = RunConfig(ticker="NVDA", date="2026-03-23")
    run = store.create(config)
    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        MockGraph.return_value = _mock_graph([("trader", "buy signal")], decision="SELL")
        events = list(service.stream_events(run.id))

    complete = next(e for e in events if e["event"] == "run:complete")
    assert complete["data"]["decision"] == "SELL"


def test_store_status_set_to_complete(service, store):
    config = RunConfig(ticker="NVDA", date="2026-03-23")
    run = store.create(config)
    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        MockGraph.return_value = _mock_graph([])
        list(service.stream_events(run.id))

    assert store.get(run.id).status == RunStatus.COMPLETE


def test_error_during_stream_emits_run_error(service, store):
    config = RunConfig(ticker="NVDA", date="2026-03-23")
    run = store.create(config)

    def bad_stream(*args, **kwargs):
        yield ("market_analyst", "ok")
        raise RuntimeError("LLM network error")

    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        mock = MagicMock()
        mock.stream_propagate.side_effect = bad_stream
        MockGraph.return_value = mock
        events = list(service.stream_events(run.id))

    error_events = [e for e in events if e["event"] == "run:error"]
    assert len(error_events) == 1
    assert "LLM network error" in error_events[0]["data"]["message"]
    # Also verify the store recorded the error
    assert store.get(run.id).error is not None
    assert "LLM network error" in store.get(run.id).error


def test_selected_analysts_passed_to_graph(service, store):
    config = RunConfig(ticker="NVDA", date="2026-03-23",
                       enabled_analysts=["market", "news"])
    run = store.create(config)
    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        MockGraph.return_value = _mock_graph([])
        list(service.stream_events(run.id))

    call_kwargs = MockGraph.call_args.kwargs
    assert call_kwargs.get("selected_analysts") == ["market", "news"]


def test_completed_run_replays_without_re_running_graph(service, store):
    # Pre-populate a completed run in the store
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.add_report(run.id, "market_analyst:0", "bullish")
    store.update_status(run.id, RunStatus.COMPLETE)
    store.update_decision(run.id, "BUY")

    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        events = list(service.stream_events(run.id))

    assert MockGraph.call_count == 0  # no agent execution on replay
    agent_completes = [e for e in events if e["event"] == "agent:complete"]
    assert len(agent_completes) == 1
    assert agent_completes[0]["data"]["report"] == "bullish"
    run_complete = next(e for e in events if e["event"] == "run:complete")
    assert run_complete["data"]["decision"] == "BUY"


def test_reconnect_to_running_run_replays_stored_events(service, store):
    """Navigating away and back while a run is in progress replays stored events
    and waits for completion — no error, no second pipeline execution."""
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.add_report(run.id, "market_analyst:0", "bullish signal")
    store.add_token_usage(run.id, "market_analyst:0", {"tokens_in": 100, "tokens_out": 50})

    # Simulate the pipeline completing on the first poll cycle.
    # We control store.get so that after the first snapshot read (replay),
    # subsequent reads return COMPLETE status.
    original_get = store.get
    call_count = {"n": 0}

    def get_with_completion(run_id):
        call_count["n"] += 1
        if call_count["n"] == 2:
            # Second read = first poll: pipeline "finished" while we were away
            store.update_decision(run_id, "BUY")
            store.update_status(run_id, RunStatus.COMPLETE)
        return original_get(run_id)

    with patch.object(store, "get", side_effect=get_with_completion):
        with patch("api.services.run_service.time.sleep"):  # skip sleep
            with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
                events = list(service.stream_events(run.id))

    assert MockGraph.call_count == 0  # no second pipeline

    agent_completes = [e for e in events if e["event"] == "agent:complete"]
    assert len(agent_completes) == 1
    assert agent_completes[0]["data"]["step"] == "market_analyst"
    assert agent_completes[0]["data"]["report"] == "bullish signal"
    assert agent_completes[0]["data"]["tokens_in"] == 100
    assert agent_completes[0]["data"]["tokens_out"] == 50

    run_completes = [e for e in events if e["event"] == "run:complete"]
    assert len(run_completes) == 1
    assert run_completes[0]["data"]["decision"] == "BUY"


def test_reconnect_to_running_run_picks_up_new_events(service, store):
    """Events added to the store while polling are streamed to the reconnected client."""
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.add_report(run.id, "market_analyst:0", "market done")

    original_get = store.get
    call_count = {"n": 0}

    def get_with_new_event(run_id):
        call_count["n"] += 1
        if call_count["n"] == 2:
            # On first poll, a new event appeared and run is now complete
            store.add_report(run_id, "news_analyst:0", "news done")
            store.update_decision(run_id, "SELL")
            store.update_status(run_id, RunStatus.COMPLETE)
        return original_get(run_id)

    with patch.object(store, "get", side_effect=get_with_new_event):
        with patch("api.services.run_service.time.sleep"):
            with patch("api.services.run_service.TradingAgentsGraph"):
                events = list(service.stream_events(run.id))

    steps = [e["data"]["step"] for e in events if e["event"] == "agent:complete"]
    assert "market_analyst" in steps
    assert "news_analyst" in steps  # picked up during poll

    run_completes = [e for e in events if e["event"] == "run:complete"]
    assert run_completes[0]["data"]["decision"] == "SELL"


def test_reconnect_to_running_run_emits_error_if_pipeline_fails(service, store):
    """If the pipeline errors while polling, a run:error is emitted."""
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.update_status(run.id, RunStatus.RUNNING)

    original_get = store.get
    call_count = {"n": 0}

    def get_with_error(run_id):
        call_count["n"] += 1
        if call_count["n"] == 2:
            store.set_error(run_id, "LLM timed out")
        return original_get(run_id)

    with patch.object(store, "get", side_effect=get_with_error):
        with patch("api.services.run_service.time.sleep"):
            with patch("api.services.run_service.TradingAgentsGraph"):
                events = list(service.stream_events(run.id))

    error_events = [e for e in events if e["event"] == "run:error"]
    assert len(error_events) == 1
    assert "LLM timed out" in error_events[0]["data"]["message"]


def test_error_run_retries_and_clears_reports(service, store):
    # Simulate a run that failed partway through with a stale report
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.add_report(run.id, "market_analyst:0", "stale data")
    store.set_error(run.id, "timeout")

    assert store.get(run.id).status == RunStatus.ERROR
    assert store.get(run.id).reports == {"market_analyst:0": "stale data"}

    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        MockGraph.return_value = _mock_graph([("news_analyst", "fresh")], decision="HOLD")
        events = list(service.stream_events(run.id))

    assert MockGraph.call_count == 1  # graph was executed on retry
    final_reports = store.get(run.id).reports
    assert "news_analyst:0" in final_reports
    assert "market_analyst:0" not in final_reports  # stale data cleared on retry


def test_live_run_agent_complete_includes_token_fields(service, store):
    """agent:complete events must include tokens_in and tokens_out."""
    config = RunConfig(ticker="NVDA", date="2026-03-23")
    run = store.create(config)
    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        MockGraph.return_value = _mock_graph([("market_analyst", "bullish")])
        events = list(service.stream_events(run.id))

    complete_events = [e for e in events if e["event"] == "agent:complete"]
    assert len(complete_events) == 1
    data = complete_events[0]["data"]
    assert "tokens_in" in data
    assert "tokens_out" in data
    assert isinstance(data["tokens_in"], int)
    assert isinstance(data["tokens_out"], int)


def test_retry_clears_stale_token_usage(service, store):
    """After an errored run is retried, stale token keys are absent."""
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.add_token_usage(run.id, "market_analyst:0", {"tokens_in": 500, "tokens_out": 200})
    store.set_error(run.id, "timeout")

    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        MockGraph.return_value = _mock_graph([("news_analyst", "fresh")])
        list(service.stream_events(run.id))

    final = store.get(run.id)
    assert "market_analyst:0" not in final.token_usage  # stale key gone
    assert "news_analyst:0" in final.token_usage         # new key present


def test_replay_attaches_token_data_to_agent_complete(service, store):
    """Replaying a completed run emits agent:complete with token data."""
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.add_report(run.id, "market_analyst:0", "bullish")
    store.add_token_usage(run.id, "market_analyst:0", {"tokens_in": 1200, "tokens_out": 400})
    store.update_status(run.id, RunStatus.COMPLETE)
    store.update_decision(run.id, "BUY")

    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        events = list(service.stream_events(run.id))

    assert MockGraph.call_count == 0
    complete_events = [e for e in events if e["event"] == "agent:complete"]
    assert len(complete_events) == 1
    assert complete_events[0]["data"]["tokens_in"] == 1200
    assert complete_events[0]["data"]["tokens_out"] == 400


def test_replay_defaults_to_zero_tokens_when_missing(service, store):
    """Replay of a run with no token_usage emits tokens_in=0, tokens_out=0."""
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.add_report(run.id, "market_analyst:0", "bearish")
    store.update_status(run.id, RunStatus.COMPLETE)
    store.update_decision(run.id, "SELL")
    # No add_token_usage call — simulates old run with no token data

    with patch("api.services.run_service.TradingAgentsGraph"):
        events = list(service.stream_events(run.id))

    complete = next(e for e in events if e["event"] == "agent:complete")
    assert complete["data"]["tokens_in"] == 0
    assert complete["data"]["tokens_out"] == 0


def test_concurrent_sse_requests_start_only_one_pipeline(store):
    """Two simultaneous SSE connections for the same QUEUED run must not launch
    two pipelines — only the first caller that wins try_claim_run starts a thread.

    Uses real threads and a barrier event to force genuine concurrency: t1 claims
    the run and starts a slow pipeline, then t2 connects while the pipeline is still
    running. Only one pipeline must be created; both streams must deliver run:complete.
    """
    config = RunConfig(ticker="NVDA", date="2026-03-23")
    run = store.create(config)
    service = RunService(store)

    pipeline_start_count = 0
    pipeline_started = threading.Event()
    pipeline_proceed = threading.Event()

    def slow_pipeline(run_id, cfg, cancel_event):
        nonlocal pipeline_start_count
        pipeline_start_count += 1
        pipeline_started.set()
        pipeline_proceed.wait(timeout=5)
        store.update_status(run_id, RunStatus.COMPLETE)
        store.update_decision(run_id, "BUY")

    results = [None, None]

    def run_stream(index):
        with patch("api.services.run_service.TradingAgentsGraph"):
            with patch("api.services.run_service.time.sleep"):
                with patch.object(service, "_run_pipeline", side_effect=slow_pipeline):
                    results[index] = list(service.stream_events(run.id))

    t1 = threading.Thread(target=run_stream, args=(0,))
    t1.start()
    pipeline_started.wait(timeout=5)   # t1 has claimed run and started pipeline

    t2 = threading.Thread(target=run_stream, args=(1,))
    t2.start()                          # t2 connects while pipeline is running

    pipeline_proceed.set()              # let the pipeline finish
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not t1.is_alive(), "t1 timed out"
    assert not t2.is_alive(), "t2 timed out"
    assert pipeline_start_count == 1
    assert any(e["event"] == "run:complete" for e in results[0])
    assert any(e["event"] == "run:complete" for e in results[1])


def test_pipeline_stops_after_cancel_event_set(store):
    """Pipeline loop exits when cancel event is set; COMPLETE is never written."""
    config = RunConfig(ticker="NVDA", date="2026-03-25")
    run = store.create(config)
    service = RunService(store)

    def yields_then_cancel():
        yield ("market_analyst", "report 1")
        # Simulate abort arriving before the next iteration
        store.try_abort_run(run.id)
        with service._cancel_lock:
            evt = service._cancel_events.get(run.id)
            if evt:
                evt.set()
        yield ("news_analyst", "report 2")  # should never be processed

    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        mock = MagicMock()
        mock.stream_propagate.return_value = yields_then_cancel()
        mock._last_decision = "BUY"
        MockGraph.return_value = mock
        with patch("api.services.run_service.time.sleep"):
            events = list(service.stream_events(run.id))

    final = store.get(run.id)
    assert final.status == RunStatus.ABORTED
    # news_analyst step should not have been processed
    assert not any(
        e["event"] == "agent:complete" and e["data"]["step"] == "news_analyst"
        for e in events
    )

def test_abort_run_sets_cancel_event_and_db(store):
    """abort_run() writes ABORTED to DB and signals the in-memory cancel event."""
    config = RunConfig(ticker="NVDA", date="2026-03-25")
    run = store.create(config)
    service = RunService(store)

    # Inject a cancel event as if a pipeline is running
    evt = threading.Event()
    with service._cancel_lock:
        service._cancel_events[run.id] = evt
    store.update_status(run.id, RunStatus.RUNNING)

    result = service.abort_run(run.id)

    assert result is True
    assert evt.is_set()
    assert store.get(run.id).status == RunStatus.ABORTED

def test_abort_run_noop_for_complete(store):
    config = RunConfig(ticker="NVDA", date="2026-03-25")
    run = store.create(config)
    store.update_status(run.id, RunStatus.COMPLETE)
    service = RunService(store)
    assert service.abort_run(run.id) is False
    assert store.get(run.id).status == RunStatus.COMPLETE


def test_poll_events_emits_run_aborted_on_aborted_status(store):
    """_poll_events yields run:aborted when it sees ABORTED status."""
    config = RunConfig(ticker="NVDA", date="2026-03-25")
    run = store.create(config)
    store.update_status(run.id, RunStatus.RUNNING)
    store.try_abort_run(run.id)
    service = RunService(store)
    with patch("api.services.run_service.time.sleep"):
        events = list(service._poll_events(run.id))
    assert any(e["event"] == "run:aborted" for e in events)
    assert not any(e["event"] == "run:complete" for e in events)
    assert not any(e["event"] == "run:error" for e in events)

def test_stream_events_replays_partial_reports_for_aborted_run(store):
    """stream_events on an ABORTED run replays partial reports then emits run:aborted."""
    config = RunConfig(ticker="NVDA", date="2026-03-25")
    run = store.create(config)
    store.update_status(run.id, RunStatus.RUNNING)
    store.add_report(run.id, "market_analyst:0", "partial report")
    store.try_abort_run(run.id)
    service = RunService(store)
    events = list(service.stream_events(run.id))
    assert any(e["event"] == "agent:complete" and e["data"]["step"] == "market_analyst"
               for e in events)
    assert events[-1]["event"] == "run:aborted"


class TestBacktestMetricsReport:
    """Tests for the backtest_metrics:0 structured JSON report."""

    def _make_fake_backtest_loop(self, events=()):
        events = tuple(events)

        class FakeBacktestLoop:
            def __init__(self, feed, strategy, risk, simulator, portfolio, config):
                pass

            def run(self, ticker, start, end):
                from tradingagents.engine.schemas.portfolio import (
                    BacktestResult, PortfolioState, PortfolioMetrics,
                )
                from datetime import date as _date, datetime, timezone
                from decimal import Decimal
                now = datetime(2024, 1, 2, tzinfo=timezone.utc)
                state = PortfolioState(
                    as_of=now, cash=Decimal("95000"), positions={"AAPL": Decimal("10")},
                    cost_basis={"AAPL": Decimal("500")},
                )
                metrics = PortfolioMetrics(
                    as_of=now,
                    total_equity=Decimal("96500"),
                    unrealized_pnl=Decimal("1500"),
                    realized_pnl=Decimal("200"),
                    total_fees_paid=Decimal("5"),
                    max_drawdown_pct=None,
                )
                return BacktestResult(
                    symbol="AAPL",
                    start=_date(2024, 1, 2),
                    end=_date(2024, 1, 10),
                    initial_state=state,
                    final_state=state,
                    events=events,
                    metrics=metrics,
                )
        return FakeBacktestLoop

    def _run_backtest(self, service, store, events=()):
        from unittest.mock import MagicMock, patch
        import threading
        from api.models.run import RunConfig, SimulationConfigSchema
        from api.store.runs_store import RunsStore

        config = RunConfig(
            ticker="AAPL",
            date="2024-01-02",
            mode="backtest",
            end_date="2024-01-10",
            simulation_config={"initial_cash": 100000, "max_position_pct": 10},
        )
        run = store.create(config)
        assert store.try_claim_run(run.id) is True

        sim_cfg = service._normalize_sim_config(config)
        cancel = threading.Event()
        FakeBacktestLoop = self._make_fake_backtest_loop(events)

        with patch("api.services.run_service.BacktestLoop", FakeBacktestLoop), \
             patch("tradingagents.engine.adapters.csv_feed.CsvDataFeed") as mock_feed, \
             patch("tradingagents.engine.adapters.langgraph_strategy.LangGraphStrategyAdapter") as mock_strategy:
            mock_feed.return_value = MagicMock()
            mock_strategy.return_value = MagicMock(close=MagicMock())
            service._run_backtest_pipeline(run.id, config, sim_cfg, cancel)

        return run.id

    def test_backtest_stores_headline_report(self, service, store):
        """Layer 2: one-line headline stored alongside metrics (same facts)."""
        run_id = self._run_backtest(service, store)
        reports = store.get(run_id).reports
        assert "backtest_headline:0" in reports
        headline = reports["backtest_headline:0"]
        assert "AAPL" in headline
        assert "fills" in headline.lower()
        assert "Final" in headline

    def test_backtest_stores_metrics_report(self, service, store):
        """After a backtest run, backtest_metrics:0 is stored with valid JSON."""
        import json
        run_id = self._run_backtest(service, store)
        reports = store.get(run_id).reports
        assert "backtest_metrics:0" in reports
        # Must be valid JSON
        parsed = json.loads(reports["backtest_metrics:0"])
        assert isinstance(parsed, dict)

    def test_backtest_metrics_json_has_expected_keys(self, service, store):
        """The stored JSON has all required BacktestMetricsPayload fields."""
        import json
        run_id = self._run_backtest(service, store)
        reports = store.get(run_id).reports
        assert "backtest_metrics:0" in reports

        parsed = json.loads(reports["backtest_metrics:0"])

        required_keys = {
            "initial_cash", "final_equity", "total_return_pct",
            "unrealized_pnl", "realized_pnl", "total_fees_paid",
            "fill_count", "max_drawdown_pct", "as_of", "positions",
            "terminal_exposure",
        }
        for key in required_keys:
            assert key in parsed, f"Missing key: {key}"

        assert parsed["fill_count"] == 0
        assert parsed["positions"] == {"AAPL": "10"}
        assert parsed["max_drawdown_pct"] is None
        assert parsed["terminal_exposure"] == "long"

    def test_backtest_persists_trace_with_signal_and_order(self, service, store):
        from datetime import datetime, timezone
        from decimal import Decimal
        from uuid import uuid4

        from tradingagents.engine.schemas.orders import ApprovedOrder, FillModel, Order
        from tradingagents.engine.schemas.portfolio import BacktestEvent, BacktestEventType
        from tradingagents.engine.schemas.signals import Signal, SignalDirection

        now = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)
        oid = uuid4()
        sig = Signal(
            symbol="AAPL",
            direction=SignalDirection.BUY,
            confidence=0.85,
            reasoning="test reasoning",
            generated_at=now,
            source_bar_timestamp=now,
        )
        inner = Order(
            id=oid,
            symbol="AAPL",
            direction=SignalDirection.BUY,
            quantity=Decimal("5"),
            created_at=now,
            fill_model=FillModel.NEXT_OPEN,
        )
        approved = ApprovedOrder(
            order=inner, approved_at=now, approved_quantity=Decimal("5"),
        )
        ev_sig = BacktestEvent(
            event_type=BacktestEventType.SIGNAL_GENERATED,
            timestamp=now,
            symbol="AAPL",
            signal=sig,
        )
        ev_ord = BacktestEvent(
            event_type=BacktestEventType.ORDER_APPROVED,
            timestamp=now,
            symbol="AAPL",
            order=approved,
        )
        run_id = self._run_backtest(service, store, events=(ev_sig, ev_ord))
        assert store.get(run_id).backtest_trace is None
        trace = store.get(run_id, include_backtest_trace=True).backtest_trace
        assert trace is not None
        assert len(trace) == 2
        assert trace[0]["event_type"] == "SIGNAL_GENERATED"
        assert trace[0]["signal"]["direction"] == "BUY"
        assert trace[0]["signal"]["reasoning"] == "test reasoning"
        assert trace[1]["event_type"] == "ORDER_APPROVED"
        assert trace[1]["order"]["approved_quantity"] == "5"
        assert trace[1]["order"]["order"]["id"] == str(oid)

    def test_backtest_metrics_payload_null_total_return_when_no_basis(self):
        """total_return_pct may be None when initial cash is zero (division undefined)."""
        import json
        from api.models.backtest import BacktestMetricsPayload

        p = BacktestMetricsPayload(
            initial_cash=0.0,
            final_equity=0.0,
            total_return_pct=None,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            total_fees_paid=0.0,
            fill_count=0,
            max_drawdown_pct=None,
            as_of=None,
            positions={},
            terminal_exposure="flat_untraded",
        )
        parsed = json.loads(p.model_dump_json())
        assert parsed["total_return_pct"] is None


def test_pipeline_continues_after_sse_disconnect(service, store):
    """When the SSE connection closes mid-run (client navigates away), the background
    pipeline thread must continue and write all results to the store — no freezing."""
    import time as real_time

    config = RunConfig(ticker="NVDA", date="2026-03-23")
    run = store.create(config)

    with patch("api.services.run_service.TradingAgentsGraph") as MockGraph:
        MockGraph.return_value = _mock_graph(
            [("market_analyst", "bullish"), ("news_analyst", "stable")],
            decision="BUY",
        )
        with patch("api.services.run_service.time.sleep"):  # no-op sleep → fast polling
            gen = service.stream_events(run.id)
            next(gen)    # advance past thread start, receive first event
            gen.close()  # simulate client disconnect

        # Wait for the pipeline thread to finish (still inside MockGraph patch context)
        deadline = real_time.time() + 2.0
        while real_time.time() < deadline:
            if store.get(run.id).status != RunStatus.RUNNING:
                break
            real_time.sleep(0.05)

    final = store.get(run.id)
    assert final.status == RunStatus.COMPLETE, "Pipeline froze after SSE disconnect"
    assert "market_analyst:0" in final.reports
    assert "news_analyst:0" in final.reports
    assert final.decision == "BUY"
