# tradingagents/engine/types.py
from __future__ import annotations
from typing import TypeVar

T = TypeVar("T")  # Documentation scaffolding only. Not used in any TypeAlias.
# Python 3.11 does not support TypeAlias with a free TypeVar.
# Convention: use Union[ConcreteType, RejectionReason] at each callsite.
# Python 3.12+ form (for reference only): type Result[T] = T | RejectionReason
# Do NOT write: Result: TypeAlias = Union[T, RejectionReason]  ← invalid in 3.11
