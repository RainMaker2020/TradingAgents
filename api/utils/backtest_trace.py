"""Serialize backtest event traces for RunsStore persistence."""

from __future__ import annotations

import json
from collections.abc import Iterable

from tradingagents.engine.schemas.portfolio import BacktestEvent


def serialize_backtest_trace(events: Iterable[BacktestEvent]) -> str:
    return json.dumps([e.model_dump(mode="json") for e in events])
