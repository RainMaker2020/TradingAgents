# tradingagents/engine/contracts/strategy.py
from __future__ import annotations
from typing import Protocol, Union, runtime_checkable
from tradingagents.engine.schemas.market import MarketState
from tradingagents.engine.schemas.signals import Signal
from tradingagents.engine.schemas.orders import RejectionReason


@runtime_checkable
class StrategyAgent(Protocol):
    def generate_signal(
        self,
        market_state: MarketState,
        # No SimulationConfig — strategy must not couple to execution/risk config.
        # Threshold config is injected at construction by concrete implementations.
    ) -> Union[Signal, RejectionReason]:
        # RejectionReason(STRATEGY_TIMEOUT): LLM/agent did not respond in time.
        # RejectionReason(INSUFFICIENT_CONTEXT): bars_window too short.
        ...
