# tradingagents/engine/adapters/langgraph_strategy.py
"""StrategyAgent adapter: drives TradingAgentsGraph for each bar."""
from __future__ import annotations
from datetime import timezone
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Union

from tradingagents.engine.adapters.signal_decision_cache import SignalDecisionCache
from tradingagents.engine.schemas.market import MarketState
from tradingagents.engine.schemas.orders import RejectionCode, RejectionReason
from tradingagents.engine.schemas.portfolio import PortfolioState
from tradingagents.engine.schemas.signals import Signal, SignalDirection

UTC = timezone.utc

_VERDICT_TO_DIRECTION: dict[str, SignalDirection] = {
    "BUY": SignalDirection.BUY,
    "SELL": SignalDirection.SELL,
    "HOLD": SignalDirection.HOLD,
}


class LangGraphStrategyAdapter:
    """Wraps TradingAgentsGraph as a StrategyAgent for BacktestLoop.

    On each generate_signal() call:
      1. Extracts symbol and trade_date from MarketState.latest_bar.
      2. Calls TradingAgentsGraph.propagate() — runs the full multi-agent pipeline.
      3. Maps the verdict (BUY/SELL/HOLD) to a Signal.
      4. Returns RejectionReason on timeout or any other failure.

    TradingAgentsGraph checkpoints each run by (ticker, date) hash, so repeated
    calls for the same bar resume from the checkpoint rather than re-running the
    entire pipeline. This is intentional: backtest runs can be interrupted and
    continued safely.

    Args:
        selected_analysts: Which analyst agents to include in the pipeline.
            Defaults to all four: ["market", "social", "news", "fundamentals"].
        config: Optional dict merged into DEFAULT_CONFIG (e.g. to override
            llm_provider, results_dir, or model names).
        confidence: Fixed confidence value for every emitted Signal (0.0–1.0).
            The multi-agent pipeline does not produce a numeric confidence score,
            so this value is supplied at construction time.
        callbacks: Optional LangChain callback handlers (e.g. for cost tracking).
    """

    def __init__(
        self,
        selected_analysts: List[str] | None = None,
        config: Dict[str, Any] | None = None,
        confidence: float = 0.8,
        callbacks: Optional[List] = None,
        enable_signal_cache: bool = True,
        prompt_version: str = "v1",
        max_retry_attempts: int = 3,
        retry_base_delay_seconds: float = 1.0,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        # Deferred import: TradingAgentsGraph is heavy (LLM clients, SQLite store).
        # Importing here avoids the startup cost when the adapter is not used.
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        self._graph = TradingAgentsGraph(
            selected_analysts=selected_analysts
            or ["market", "social", "news", "fundamentals"],
            config=config,
            callbacks=callbacks,
        )
        self._confidence = confidence
        self._enable_signal_cache = enable_signal_cache
        self._prompt_version = prompt_version
        self._max_retry_attempts = max(1, int(max_retry_attempts))
        self._retry_base_delay_seconds = max(0.0, float(retry_base_delay_seconds))
        self._should_cancel = should_cancel
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache = SignalDecisionCache(
            db_path=self._signal_cache_path(self._graph.config),
            enabled=self._enable_signal_cache,
        )

    def generate_signal(
        self,
        market_state: MarketState,
        portfolio: PortfolioState | None = None,
    ) -> Union[Signal, RejectionReason]:
        del portfolio  # graph verdict does not use portfolio state today
        if self._is_cancelled():
            return RejectionReason(
                code=RejectionCode.STRATEGY_TIMEOUT,
                detail="backtest run cancelled",
            )
        symbol = market_state.symbol
        trade_date = str(market_state.latest_bar.timestamp.date())
        key_payload = self._build_key_payload(symbol, trade_date)

        cached = self._cache.get(key_payload)
        if cached is not None:
            cached_decision = str(cached.get("decision", "")).upper()
            if cached_decision in _VERDICT_TO_DIRECTION:
                self._cache_hits += 1
                return Signal(
                    symbol=symbol,
                    direction=_VERDICT_TO_DIRECTION[cached_decision],
                    confidence=self._confidence,
                    reasoning=str(cached.get("reasoning") or cached_decision),
                    generated_at=market_state.as_of,
                    source_bar_timestamp=market_state.latest_bar.timestamp,
                )

        self._cache_misses += 1
        try:
            final_state, decision = self._propagate_with_retry(symbol, trade_date)
        except _RunCancelledError:
            return RejectionReason(
                code=RejectionCode.STRATEGY_TIMEOUT,
                detail="backtest run cancelled",
            )
        except TimeoutError:
            return RejectionReason(
                code=RejectionCode.STRATEGY_TIMEOUT,
                detail="TradingAgentsGraph timed out",
            )
        except Exception as exc:
            # Provider/network/SDK errors should not crash the full backtest loop.
            # Convert them to a strategy-stage rejection so orchestration can continue.
            return RejectionReason(
                code=RejectionCode.INSUFFICIENT_CONTEXT,
                detail=f"graph error [{type(exc).__name__}]: {exc}",
            )

        if decision not in _VERDICT_TO_DIRECTION:
            return RejectionReason(
                code=RejectionCode.INSUFFICIENT_CONTEXT,
                detail=f"graph returned no valid verdict (got {decision!r})",
            )

        direction = _VERDICT_TO_DIRECTION[decision]

        # Use catalyst as Signal.reasoning; fall back to investment_plan or raw decision.
        chief_report = final_state.get("chief_analyst_report") or {}
        reasoning: str = (
            chief_report.get("catalyst")
            or final_state.get("investment_plan", "")
            or decision
        )
        self._cache.set(
            key_payload,
            {
                "decision": decision,
                "reasoning": reasoning,
                "cached_from": "langgraph_strategy_adapter",
            },
        )

        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=self._confidence,
            reasoning=reasoning,
            generated_at=market_state.as_of,
            source_bar_timestamp=market_state.latest_bar.timestamp,
        )

    def close(self) -> None:
        """Release the underlying SQLite checkpoint connection."""
        self._cache.close()
        self._graph.close()

    def __enter__(self) -> "LangGraphStrategyAdapter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_cache_stats(self) -> dict[str, int]:
        stats = self._cache.stats
        stats["hits"] = self._cache_hits
        stats["misses"] = self._cache_misses
        return stats

    def _propagate_with_retry(self, symbol: str, trade_date: str) -> tuple[dict[str, Any], str]:
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retry_attempts + 1):
            if self._is_cancelled():
                raise _RunCancelledError("cancelled before graph propagate")
            try:
                return self._graph.propagate(symbol, trade_date)
            except TimeoutError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt >= self._max_retry_attempts or not self._is_retryable_error(exc):
                    raise
                delay = self._retry_base_delay_seconds * (2 ** (attempt - 1))
                self._sleep_with_cancel(delay)
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("retry loop exited unexpectedly without result")

    def _sleep_with_cancel(self, delay_seconds: float) -> None:
        if delay_seconds <= 0:
            return
        deadline = time.monotonic() + delay_seconds
        while True:
            if self._is_cancelled():
                raise _RunCancelledError("cancelled during retry backoff")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 0.1))

    def _is_cancelled(self) -> bool:
        should_cancel = getattr(self, "_should_cancel", None)
        return bool(should_cancel and should_cancel())

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        if isinstance(exc, (ConnectionError, OSError)):
            return True
        detail = str(exc).lower()
        return any(token in detail for token in (
            "429",
            "rate limit",
            "temporar",
            "timeout",
            "timed out",
            "service unavailable",
            "too many requests",
            "connection reset",
        ))

    def _build_key_payload(self, symbol: str, trade_date: str) -> dict[str, Any]:
        cfg = getattr(self._graph, "config", {}) or {}
        return {
            "cache_version": 1,
            "prompt_version": self._prompt_version,
            "symbol": symbol.strip().upper(),
            "trade_date": trade_date,
            "analysts": sorted(list(getattr(self._graph, "selected_analysts", []))),
            "llm_provider": cfg.get("llm_provider"),
            "deep_think_llm": cfg.get("deep_think_llm"),
            "quick_think_llm": cfg.get("quick_think_llm"),
            "max_debate_rounds": cfg.get("max_debate_rounds"),
            "max_risk_discuss_rounds": cfg.get("max_risk_discuss_rounds"),
            "backend_url": cfg.get("backend_url"),
            "google_thinking_level": cfg.get("google_thinking_level"),
            "openai_reasoning_effort": cfg.get("openai_reasoning_effort"),
        }

    @staticmethod
    def _signal_cache_path(config: dict[str, Any]) -> Path:
        results_dir = Path(config.get("results_dir", "./results")).expanduser().resolve()
        return results_dir / ".cache" / "signal_decisions.sqlite"


class _RunCancelledError(RuntimeError):
    pass
