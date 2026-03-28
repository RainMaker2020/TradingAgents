"""Behavior tests for LangGraphStrategyAdapter error handling."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

from tradingagents.engine.adapters.langgraph_strategy import LangGraphStrategyAdapter
from tradingagents.engine.schemas.market import MarketState
from tradingagents.engine.schemas.orders import RejectionCode, RejectionReason

from tests.engine.fakes import make_bar

UTC = timezone.utc


def _market_state() -> MarketState:
    bar = make_bar(ts=datetime(2026, 1, 2, tzinfo=UTC))
    return MarketState(
        symbol="AAPL",
        as_of=bar.timestamp,
        latest_bar=bar,
        bars_window=(bar,),
    )


class _TimeoutGraph:
    def propagate(self, symbol: str, trade_date: str):
        raise TimeoutError("simulated timeout")

    def close(self) -> None:
        return None


class _ProviderFailureGraph:
    def __init__(self) -> None:
        self.calls = 0

    def propagate(self, symbol: str, trade_date: str):
        self.calls += 1
        raise RuntimeError("429 rate limit")

    def close(self) -> None:
        return None


def test_timeout_maps_to_strategy_timeout_rejection():
    adapter = LangGraphStrategyAdapter.__new__(LangGraphStrategyAdapter)
    adapter._graph = _TimeoutGraph()  # type: ignore[attr-defined]
    adapter._confidence = 0.8  # type: ignore[attr-defined]
    adapter._enable_signal_cache = False  # type: ignore[attr-defined]
    adapter._prompt_version = "v1"  # type: ignore[attr-defined]
    adapter._cache_hits = 0  # type: ignore[attr-defined]
    adapter._cache_misses = 0  # type: ignore[attr-defined]
    adapter._cache = _MemoryCache()  # type: ignore[attr-defined]
    adapter._max_retry_attempts = 2  # type: ignore[attr-defined]
    adapter._retry_base_delay_seconds = 0.0  # type: ignore[attr-defined]

    result = adapter.generate_signal(_market_state())

    assert isinstance(result, RejectionReason)
    assert result.code == RejectionCode.STRATEGY_TIMEOUT


def test_non_timeout_provider_error_maps_to_insufficient_context_rejection():
    adapter = LangGraphStrategyAdapter.__new__(LangGraphStrategyAdapter)
    adapter._graph = _ProviderFailureGraph()  # type: ignore[attr-defined]
    adapter._confidence = 0.8  # type: ignore[attr-defined]
    adapter._enable_signal_cache = False  # type: ignore[attr-defined]
    adapter._prompt_version = "v1"  # type: ignore[attr-defined]
    adapter._cache_hits = 0  # type: ignore[attr-defined]
    adapter._cache_misses = 0  # type: ignore[attr-defined]
    adapter._cache = _MemoryCache()  # type: ignore[attr-defined]
    adapter._max_retry_attempts = 2  # type: ignore[attr-defined]
    adapter._retry_base_delay_seconds = 0.0  # type: ignore[attr-defined]

    result = adapter.generate_signal(_market_state())

    assert isinstance(result, RejectionReason)
    assert result.code == RejectionCode.INSUFFICIENT_CONTEXT
    assert result.detail is not None
    assert "RuntimeError" in result.detail


class _CountingGraph:
    def __init__(self) -> None:
        self.calls = 0
        self.selected_analysts = ["market", "fundamentals"]
        self.config = {
            "results_dir": "./results",
            "llm_provider": "deepseek",
            "deep_think_llm": "deepseek-chat",
            "quick_think_llm": "deepseek-chat",
            "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 1,
            "backend_url": "https://api.deepseek.com/v1",
            "google_thinking_level": None,
            "openai_reasoning_effort": None,
        }

    def propagate(self, symbol: str, trade_date: str):
        self.calls += 1
        return (
            {"chief_analyst_report": {"catalyst": f"catalyst-{trade_date}"}},
            "BUY",
        )

    def close(self) -> None:
        return None


class _RetryThenSuccessGraph:
    def __init__(self) -> None:
        self.calls = 0
        self.selected_analysts = ["market"]
        self.config = {"results_dir": "./results"}

    def propagate(self, symbol: str, trade_date: str):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("429 rate limit")
        return ({"chief_analyst_report": {"catalyst": "recovered"}}, "BUY")

    def close(self) -> None:
        return None


class _NonRetryableGraph:
    def __init__(self) -> None:
        self.calls = 0
        self.selected_analysts = ["market"]
        self.config = {"results_dir": "./results"}

    def propagate(self, symbol: str, trade_date: str):
        self.calls += 1
        raise ValueError("invalid prompt schema")

    def close(self) -> None:
        return None


class _ShouldNotBeCalledGraph:
    def __init__(self) -> None:
        self.calls = 0
        self.selected_analysts = ["market"]
        self.config = {"results_dir": "./results"}

    def propagate(self, symbol: str, trade_date: str):
        self.calls += 1
        return ({"chief_analyst_report": {"catalyst": "unused"}}, "BUY")

    def close(self) -> None:
        return None


class _MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self.stats = {"read_errors": 0, "write_errors": 0}

    def _key(self, payload: dict) -> str:
        return json.dumps(payload, sort_keys=True)

    def get(self, payload: dict):
        return self._store.get(self._key(payload))

    def set(self, payload: dict, value: dict) -> None:
        self._store[self._key(payload)] = value

    def close(self) -> None:
        return None


def test_cache_hit_skips_graph_propagate():
    ms = _market_state()
    graph = _CountingGraph()
    cache = _MemoryCache()

    adapter = LangGraphStrategyAdapter.__new__(LangGraphStrategyAdapter)
    adapter._graph = graph  # type: ignore[attr-defined]
    adapter._confidence = 0.8  # type: ignore[attr-defined]
    adapter._enable_signal_cache = True  # type: ignore[attr-defined]
    adapter._prompt_version = "v1"  # type: ignore[attr-defined]
    adapter._cache_hits = 0  # type: ignore[attr-defined]
    adapter._cache_misses = 0  # type: ignore[attr-defined]
    adapter._cache = cache  # type: ignore[attr-defined]
    adapter._max_retry_attempts = 2  # type: ignore[attr-defined]
    adapter._retry_base_delay_seconds = 0.0  # type: ignore[attr-defined]

    key_payload = adapter._build_key_payload(ms.symbol, str(ms.latest_bar.timestamp.date()))  # type: ignore[attr-defined]
    cache.set(key_payload, {"decision": "BUY", "reasoning": "cached reason"})

    result = adapter.generate_signal(ms)

    assert graph.calls == 0
    assert result.direction.name == "BUY"
    assert result.reasoning == "cached reason"
    assert adapter.get_cache_stats()["hits"] == 1  # type: ignore[attr-defined]


def test_cache_miss_calls_graph_once_then_hits_cache():
    ms = _market_state()
    graph = _CountingGraph()
    cache = _MemoryCache()

    adapter = LangGraphStrategyAdapter.__new__(LangGraphStrategyAdapter)
    adapter._graph = graph  # type: ignore[attr-defined]
    adapter._confidence = 0.8  # type: ignore[attr-defined]
    adapter._enable_signal_cache = True  # type: ignore[attr-defined]
    adapter._prompt_version = "v1"  # type: ignore[attr-defined]
    adapter._cache_hits = 0  # type: ignore[attr-defined]
    adapter._cache_misses = 0  # type: ignore[attr-defined]
    adapter._cache = cache  # type: ignore[attr-defined]
    adapter._max_retry_attempts = 2  # type: ignore[attr-defined]
    adapter._retry_base_delay_seconds = 0.0  # type: ignore[attr-defined]

    first = adapter.generate_signal(ms)
    second = adapter.generate_signal(ms)

    assert graph.calls == 1
    assert first.direction.name == "BUY"
    assert second.direction.name == "BUY"
    stats = adapter.get_cache_stats()  # type: ignore[attr-defined]
    assert stats["misses"] == 1
    assert stats["hits"] == 1


def test_retryable_provider_error_retries_then_succeeds():
    ms = _market_state()
    graph = _RetryThenSuccessGraph()

    adapter = LangGraphStrategyAdapter.__new__(LangGraphStrategyAdapter)
    adapter._graph = graph  # type: ignore[attr-defined]
    adapter._confidence = 0.8  # type: ignore[attr-defined]
    adapter._enable_signal_cache = False  # type: ignore[attr-defined]
    adapter._prompt_version = "v1"  # type: ignore[attr-defined]
    adapter._cache_hits = 0  # type: ignore[attr-defined]
    adapter._cache_misses = 0  # type: ignore[attr-defined]
    adapter._cache = _MemoryCache()  # type: ignore[attr-defined]
    adapter._max_retry_attempts = 3  # type: ignore[attr-defined]
    adapter._retry_base_delay_seconds = 0.0  # type: ignore[attr-defined]

    with patch("tradingagents.engine.adapters.langgraph_strategy.time.sleep"):
        result = adapter.generate_signal(ms)

    assert graph.calls == 2
    assert result.direction.name == "BUY"


def test_retryable_provider_error_exhausts_retries():
    ms = _market_state()
    graph = _ProviderFailureGraph()

    adapter = LangGraphStrategyAdapter.__new__(LangGraphStrategyAdapter)
    adapter._graph = graph  # type: ignore[attr-defined]
    adapter._confidence = 0.8  # type: ignore[attr-defined]
    adapter._enable_signal_cache = False  # type: ignore[attr-defined]
    adapter._prompt_version = "v1"  # type: ignore[attr-defined]
    adapter._cache_hits = 0  # type: ignore[attr-defined]
    adapter._cache_misses = 0  # type: ignore[attr-defined]
    adapter._cache = _MemoryCache()  # type: ignore[attr-defined]
    adapter._max_retry_attempts = 2  # type: ignore[attr-defined]
    adapter._retry_base_delay_seconds = 0.0  # type: ignore[attr-defined]

    with patch("tradingagents.engine.adapters.langgraph_strategy.time.sleep"):
        result = adapter.generate_signal(ms)

    assert isinstance(result, RejectionReason)
    assert result.code == RejectionCode.INSUFFICIENT_CONTEXT
    assert graph.calls == 2


def test_non_retryable_error_fails_without_extra_attempts():
    ms = _market_state()
    graph = _NonRetryableGraph()

    adapter = LangGraphStrategyAdapter.__new__(LangGraphStrategyAdapter)
    adapter._graph = graph  # type: ignore[attr-defined]
    adapter._confidence = 0.8  # type: ignore[attr-defined]
    adapter._enable_signal_cache = False  # type: ignore[attr-defined]
    adapter._prompt_version = "v1"  # type: ignore[attr-defined]
    adapter._cache_hits = 0  # type: ignore[attr-defined]
    adapter._cache_misses = 0  # type: ignore[attr-defined]
    adapter._cache = _MemoryCache()  # type: ignore[attr-defined]
    adapter._max_retry_attempts = 3  # type: ignore[attr-defined]
    adapter._retry_base_delay_seconds = 0.0  # type: ignore[attr-defined]

    with patch("tradingagents.engine.adapters.langgraph_strategy.time.sleep") as sleep_mock:
        result = adapter.generate_signal(ms)

    assert isinstance(result, RejectionReason)
    assert result.code == RejectionCode.INSUFFICIENT_CONTEXT
    assert graph.calls == 1
    sleep_mock.assert_not_called()


def test_cancelled_run_short_circuits_before_graph_call():
    ms = _market_state()
    graph = _ShouldNotBeCalledGraph()

    adapter = LangGraphStrategyAdapter.__new__(LangGraphStrategyAdapter)
    adapter._graph = graph  # type: ignore[attr-defined]
    adapter._confidence = 0.8  # type: ignore[attr-defined]
    adapter._enable_signal_cache = False  # type: ignore[attr-defined]
    adapter._prompt_version = "v1"  # type: ignore[attr-defined]
    adapter._cache_hits = 0  # type: ignore[attr-defined]
    adapter._cache_misses = 0  # type: ignore[attr-defined]
    adapter._cache = _MemoryCache()  # type: ignore[attr-defined]
    adapter._max_retry_attempts = 3  # type: ignore[attr-defined]
    adapter._retry_base_delay_seconds = 0.0  # type: ignore[attr-defined]
    adapter._should_cancel = lambda: True  # type: ignore[attr-defined]

    result = adapter.generate_signal(ms)

    assert isinstance(result, RejectionReason)
    assert result.code == RejectionCode.STRATEGY_TIMEOUT
    assert graph.calls == 0
