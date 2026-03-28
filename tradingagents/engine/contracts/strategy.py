# tradingagents/engine/contracts/strategy.py
from __future__ import annotations
from typing import Protocol, Union, runtime_checkable
from tradingagents.engine.schemas.market import MarketState
from tradingagents.engine.schemas.portfolio import PortfolioState
from tradingagents.engine.schemas.signals import Signal
from tradingagents.engine.schemas.orders import RejectionReason


@runtime_checkable
class StrategyAgent(Protocol):
    def generate_signal(
        self,
        market_state: MarketState,
        portfolio: PortfolioState | None = None,
        # No SimulationConfig — strategy must not couple to execution/risk config.
        # ``portfolio`` lets adapters run exit rules vs cost basis; omit when unknown.
    ) -> Union[Signal, RejectionReason]:
        # RejectionReason(STRATEGY_TIMEOUT): LLM/agent did not respond in time.
        # RejectionReason(INSUFFICIENT_CONTEXT): bars_window too short.
        ...
