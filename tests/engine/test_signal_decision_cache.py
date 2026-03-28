"""Unit tests for SignalDecisionCache."""
from __future__ import annotations

from pathlib import Path

from tradingagents.engine.adapters.signal_decision_cache import SignalDecisionCache


def test_roundtrip_get_set(tmp_path: Path):
    cache = SignalDecisionCache(tmp_path / "signal_decisions.sqlite", enabled=True)
    key = {
        "symbol": "AAPL",
        "trade_date": "2024-01-02",
        "llm_provider": "deepseek",
        "prompt_version": "v1",
    }
    value = {"decision": "BUY", "reasoning": "cached"}

    cache.set(key, value)
    loaded = cache.get(key)
    cache.close()

    assert loaded == value


def test_disabled_cache_is_noop(tmp_path: Path):
    cache = SignalDecisionCache(tmp_path / "signal_decisions.sqlite", enabled=False)
    key = {"symbol": "AAPL", "trade_date": "2024-01-02"}
    cache.set(key, {"decision": "BUY", "reasoning": "cached"})
    loaded = cache.get(key)
    cache.close()

    assert loaded is None
