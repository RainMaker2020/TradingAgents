"""Shared types for rule-based entry/exit helpers used by strategy adapters."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class StrategyParams:
    """Parameters for built-in technical rules (e.g. moving-average windows)."""

    short_window: int = 5
    long_window: int = 20


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    """Minimal long position view for exit rules."""

    symbol: str
    quantity: Decimal
    avg_entry_price: Decimal
