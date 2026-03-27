import logging
import time
import threading
from collections import defaultdict
from typing import Generator
from api.store.runs_store import RunsStore
from api.models.run import RunConfig, RunStatus
from api.callbacks.token_handler import TokenCallbackHandler

logger = logging.getLogger(__name__)

try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
except ImportError:
    TradingAgentsGraph = None  # type: ignore
    DEFAULT_CONFIG = {}

from tradingagents.engine.schemas.config import SimulationConfig
from tradingagents.engine.schemas.config_input import SimulationConfigInput


class RunService:
    def __init__(self, store: RunsStore):
        self._store = store
        self._cancel_events: dict[str, threading.Event] = {}
        self._cancel_lock = threading.Lock()

    @staticmethod
    def _normalize_sim_config(config: RunConfig) -> SimulationConfig:
        """Normalize user-facing SimulationConfigSchema to engine SimulationConfig.

        SimulationConfigSchema (API layer) uses user-friendly units:
          - max_position_pct as percent (10 = 10%)
          - all Decimal fields as float/int

        SimulationConfigInput converts to engine units:
          - max_position_pct as ratio (0.10)
          - all financial values as Decimal

        API accepts percent; engine stores ratio.

        This is the single normalization point. Both ``graph`` and ``backtest``
        execution paths receive the same normalized ``SimulationConfig``.
        """
        sim_schema = config.simulation_config
        if sim_schema is not None:
            return SimulationConfigInput(
                **sim_schema.model_dump(exclude_none=True)
            ).to_simulation_config()
        return SimulationConfigInput().to_simulation_config()

    def abort_run(self, run_id: str) -> bool:
        """Write ABORTED to DB first (durable), then signal the pipeline thread."""
        aborted = self._store.try_abort_run(run_id)
        if aborted:
            with self._cancel_lock:
                event = self._cancel_events.get(run_id)
                if event:
                    event.set()
        return aborted

    def _run_pipeline(self, run_id: str, config: RunConfig, cancel_event: threading.Event) -> None:
        """Dispatcher: normalize sim config once, then route to graph or backtest path.

        Both paths receive the same normalized ``SimulationConfig`` so there is
        exactly one contract and zero config drift between execution modes.
        """
        try:
            sim_cfg = self._normalize_sim_config(config)
            logger.debug(
                "run %s [mode=%s]: sim_cfg cash=%s slippage=%sbps max_pos=%s fee=%s",
                run_id, config.mode,
                sim_cfg.initial_cash, sim_cfg.slippage_bps,
                sim_cfg.max_position_pct,   # ratio (e.g. 0.10), never percent
                sim_cfg.fee_per_trade,
            )
            if config.mode == "backtest":
                self._run_backtest_pipeline(run_id, config, sim_cfg, cancel_event)
            else:
                self._run_graph_pipeline(run_id, config, sim_cfg, cancel_event)
        except Exception as e:
            # Safety net: sub-pipelines catch their own exceptions, but guard
            # here in case normalization or dispatch itself fails.
            self._store.try_error_run(run_id, str(e))
        finally:
            with self._cancel_lock:
                self._cancel_events.pop(run_id, None)

    def _run_graph_pipeline(
        self,
        run_id: str,
        config: RunConfig,
        sim_cfg: SimulationConfig,
        cancel_event: threading.Event,
    ) -> None:
        """Graph execution path: TradingAgentsGraph (LLM multi-agent analysis).

        ``sim_cfg`` is normalized and available here for future use (e.g. wiring
        ``min_confidence_threshold`` into the graph config).  Currently the graph
        uses its own defaults for these parameters.
        """
        try:
            ta_config = DEFAULT_CONFIG.copy()
            ta_config["llm_provider"]            = config.llm_provider
            ta_config["deep_think_llm"]          = config.deep_think_llm
            ta_config["quick_think_llm"]         = config.quick_think_llm
            ta_config["max_debate_rounds"]       = config.max_debate_rounds
            ta_config["max_risk_discuss_rounds"] = config.max_risk_discuss_rounds

            token_handler = TokenCallbackHandler()
            ta = TradingAgentsGraph(
                debug=False,
                config=ta_config,
                selected_analysts=config.enabled_analysts or
                    ["market", "news", "fundamentals", "social"],
                callbacks=[token_handler],
            )

            turn_counts: defaultdict[str, int] = defaultdict(int)

            for step_key, report in ta.stream_propagate(config.ticker, config.date):
                if cancel_event.is_set():
                    return  # abort requested; ABORTED already in DB
                tokens = token_handler.snapshot_and_reset()
                turn = turn_counts[step_key]
                self._store.add_report(run_id, f"{step_key}:{turn}", report)
                self._store.add_token_usage(
                    run_id, f"{step_key}:{turn}",
                    {"tokens_in": tokens["in"], "tokens_out": tokens["out"]},
                )
                turn_counts[step_key] += 1

            decision = ta._last_decision or "HOLD"
            self._store.try_complete_run(run_id, decision)

        except Exception as e:
            self._store.try_error_run(run_id, str(e))

    def _run_backtest_pipeline(
        self,
        run_id: str,
        config: RunConfig,
        sim_cfg: SimulationConfig,
        cancel_event: threading.Event,
    ) -> None:
        """Backtest execution path: BacktestLoop against cached CSV data.

        Uses MA-crossover strategy (long-only, no LLM calls).  ``sim_cfg`` is
        passed directly to BacktestLoop — cash, slippage, fees, and position
        limits all come from the normalized engine config.
        """
        from datetime import date
        from tradingagents.engine.adapters.csv_feed import CsvDataFeed
        from tradingagents.engine.adapters.toy_strategy import MovingAverageCrossStrategy
        from tradingagents.engine.runtime.backtest_loop import BacktestLoop
        from tradingagents.engine.runtime.paper_portfolio import InMemoryPortfolio
        from tradingagents.engine.runtime.simulator import ConcreteExecutionSimulator
        from tradingagents.engine.runtime.risk_manager import ConcreteRiskManager
        from tradingagents.engine.schemas.portfolio import BacktestEventType

        try:
            start = date.fromisoformat(config.date)
            end = date.fromisoformat(config.end_date) if config.end_date else start

            try:
                feed = CsvDataFeed(config.ticker)
            except FileNotFoundError as exc:
                self._store.try_error_run(run_id, str(exc))
                return

            if cancel_event.is_set():
                return

            strategy = MovingAverageCrossStrategy(
                short_window=5, long_window=20, confidence=0.8, long_only=True
            )
            result = BacktestLoop(
                feed=feed,
                strategy=strategy,
                risk=ConcreteRiskManager(),
                simulator=ConcreteExecutionSimulator(),
                portfolio=InMemoryPortfolio(),
                config=sim_cfg,          # ← normalized engine config, not percent values
            ).run(config.ticker, start, end)

            if cancel_event.is_set():
                return

            # Summarise result as a report for SSE replay
            fills = [e for e in result.events if e.event_type == BacktestEventType.FILL_EXECUTED]
            m = result.metrics
            pnl = float(m.total_equity) - float(sim_cfg.initial_cash)
            pnl_pct = pnl / float(sim_cfg.initial_cash) * 100
            summary = (
                f"Backtest: {config.ticker}  {start} → {end}\n"
                f"Config:   cash=${float(sim_cfg.initial_cash):,.0f}  "
                f"slippage={sim_cfg.slippage_bps}bps  "
                f"fee=${sim_cfg.fee_per_trade}/trade  "
                f"max_pos={float(sim_cfg.max_position_pct):.0%}\n"
                f"\n"
                f"Fills:         {len(fills)}\n"
                f"Final equity:  ${float(m.total_equity):,.2f}  ({pnl_pct:+.2f}%)\n"
                f"Unrealized P&L: ${float(m.unrealized_pnl):,.2f}\n"
                f"Open positions: {dict(result.final_state.positions) or 'none'}\n"
            )
            self._store.add_report(run_id, "backtest_summary:0", summary)

            # Derive a terminal decision from the final portfolio state
            if result.final_state.positions:
                decision = "BUY"   # still holding at least one position
            elif fills:
                decision = "SELL"  # all positions liquidated
            else:
                decision = "HOLD"  # no trades executed

            self._store.try_complete_run(run_id, decision)

        except Exception as e:
            self._store.try_error_run(run_id, str(e))

    _MAX_POLL_SECONDS = 3600  # 1 hour wall-clock cap; prevents infinite hang on thread crash

    def _poll_events(self, run_id: str) -> Generator[dict, None, None]:
        """Poll SQLite and stream events until the run reaches a terminal state.

        Safe to close at any time — the pipeline thread is unaffected.
        Times out after _MAX_POLL_SECONDS if the run never reaches a terminal state.
        """
        seen_keys: set[str] = set()
        deadline = time.monotonic() + self._MAX_POLL_SECONDS
        while True:
            if time.monotonic() >= deadline:
                yield {"event": "run:error", "data": {"message": "Run timed out waiting for pipeline"}}
                return
            snapshot = self._store.get(run_id)
            token_usage = {k: v.model_dump() for k, v in (snapshot.token_usage or {}).items()}
            for key, report in snapshot.reports.items():
                if key in seen_keys or ":" not in key:
                    continue
                step_key, turn_str = key.rsplit(":", 1)
                if not turn_str.isdigit():
                    continue
                seen_keys.add(key)
                turn = int(turn_str)
                raw = token_usage.get(key, {"tokens_in": 0, "tokens_out": 0})
                yield {"event": "agent:start",    "data": {"step": step_key, "turn": turn}}
                yield {"event": "agent:complete", "data": {
                    "step": step_key, "turn": turn, "report": report,
                    "tokens_in": raw.get("tokens_in", 0),
                    "tokens_out": raw.get("tokens_out", 0),
                }}
            if snapshot.status == RunStatus.COMPLETE:
                yield {"event": "run:complete", "data": {"decision": snapshot.decision or "HOLD", "run_id": run_id}}
                return
            if snapshot.status == RunStatus.ERROR:
                yield {"event": "run:error", "data": {"message": snapshot.error or "Unknown error"}}
                return
            if snapshot.status == RunStatus.ABORTED:
                yield {"event": "run:aborted", "data": {"run_id": run_id}}
                return
            time.sleep(0.5)

    def stream_events(self, run_id: str) -> Generator[dict, None, None]:
        run = self._store.get(run_id)
        if not run or not run.config:
            yield {"event": "run:error", "data": {"message": "Run not found"}}
            return

        if run.status == RunStatus.COMPLETE:
            token_usage = {k: v.model_dump() for k, v in (run.token_usage or {}).items()}
            for key, report in run.reports.items():
                if ":" not in key:
                    logger.warning(
                        "Skipping malformed report key %r for run %s", key, run_id
                    )
                    continue
                step_key, turn_str = key.rsplit(":", 1)
                if not turn_str.isdigit():
                    logger.warning(
                        "Skipping report key with non-numeric turn %r for run %s", key, run_id
                    )
                    continue
                turn = int(turn_str)
                raw = token_usage.get(key, {"tokens_in": 0, "tokens_out": 0})
                yield {"event": "agent:start",    "data": {"step": step_key, "turn": turn}}
                yield {"event": "agent:complete", "data": {
                    "step": step_key, "turn": turn, "report": report,
                    "tokens_in": raw.get("tokens_in", 0),
                    "tokens_out": raw.get("tokens_out", 0),
                }}
            yield {"event": "run:complete", "data": {"decision": run.decision or "HOLD", "run_id": run_id}}
            return

        if run.status == RunStatus.ABORTED:
            # Replay partial reports collected before abort, then signal aborted
            token_usage = {k: v.model_dump() for k, v in (run.token_usage or {}).items()}
            for key, report in run.reports.items():
                if ":" not in key:
                    continue
                step_key, turn_str = key.rsplit(":", 1)
                if not turn_str.isdigit():
                    continue
                turn = int(turn_str)
                raw = token_usage.get(key, {"tokens_in": 0, "tokens_out": 0})
                yield {"event": "agent:start",    "data": {"step": step_key, "turn": turn}}
                yield {"event": "agent:complete", "data": {
                    "step": step_key, "turn": turn, "report": report,
                    "tokens_in": raw.get("tokens_in", 0),
                    "tokens_out": raw.get("tokens_out", 0),
                }}
            yield {"event": "run:aborted", "data": {"run_id": run_id}}
            return

        if run.status == RunStatus.RUNNING:
            yield from self._poll_events(run_id)
            return

        # QUEUED or ERROR: atomically claim the run before starting pipeline.
        # try_claim_run does a single UPDATE ... WHERE status IN ('queued','error')
        # so concurrent SSE requests can't both start a pipeline for the same run.
        if not self._store.try_claim_run(run_id):
            # Another caller already claimed it — just poll for its results.
            yield from self._poll_events(run_id)
            return

        self._store.clear_reports(run_id)
        self._store.clear_token_usage(run_id)

        with self._cancel_lock:
            cancel_event = threading.Event()
            self._cancel_events[run_id] = cancel_event

        thread = threading.Thread(
            target=self._run_pipeline,
            args=(run_id, run.config, cancel_event),
            daemon=True,
        )
        thread.start()

        yield from self._poll_events(run_id)
