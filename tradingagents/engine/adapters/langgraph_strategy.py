# tradingagents/engine/adapters/langgraph_strategy.py
"""StrategyAgent adapter: drives TradingAgentsGraph for each bar."""
from __future__ import annotations
from datetime import timezone
from typing import Any, Dict, List, Optional, Union

from tradingagents.engine.schemas.market import MarketState
from tradingagents.engine.schemas.orders import RejectionCode, RejectionReason
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

    def generate_signal(
        self, market_state: MarketState
    ) -> Union[Signal, RejectionReason]:
        symbol = market_state.symbol
        trade_date = str(market_state.latest_bar.timestamp.date())

        try:
            final_state, decision = self._graph.propagate(symbol, trade_date)
        except TimeoutError:
            return RejectionReason(
                code=RejectionCode.STRATEGY_TIMEOUT,
                detail="TradingAgentsGraph timed out",
            )
        except (ValueError, KeyError) as exc:
            return RejectionReason(
                code=RejectionCode.INSUFFICIENT_CONTEXT,
                detail=f"graph error: {exc}",
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
        self._graph.close()

    def __enter__(self) -> "LangGraphStrategyAdapter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
