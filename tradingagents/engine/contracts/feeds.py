# tradingagents/engine/contracts/feeds.py
from __future__ import annotations
from datetime import date, datetime
from typing import Iterator, Protocol, Union, runtime_checkable
from tradingagents.engine.schemas.market import Bar
from tradingagents.engine.schemas.orders import RejectionReason


@runtime_checkable
class MarketCalendar(Protocol):
    # CONTRACT: all inputs are UTC. Implementations convert internally
    # using SimulationConfig.calendar_timezone.
    # Enforcement is by test suite only (Protocols cannot enforce invariants).
    def is_trading_day(self, dt: date) -> bool: ...
    def next_trading_day(self, dt: date) -> date: ...
    def previous_trading_day(self, dt: date) -> date: ...
    def is_session_open(self, dt: datetime) -> bool: ...  # intraday extension point


@runtime_checkable
class DataFeed(Protocol):
    calendar: MarketCalendar

    def stream_bars(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> Iterator[Union[Bar, RejectionReason]]:
        # Yields Union[Bar, RejectionReason] per calendar day in [start, end].
        # On missing bar: yields RejectionReason(DATA_UNAVAILABLE), continues.
        # On unknown symbol: yields RejectionReason(BAR_NOT_FOUND), continues.
        # MUST NOT raise for expected absence cases.
        ...

    def get_bar(
        self,
        symbol: str,
        as_of: date,
    ) -> Union[Bar, RejectionReason]:
        # Returns RejectionReason(DATA_UNAVAILABLE) if bar absent for date.
        # Returns RejectionReason(BAR_NOT_FOUND) if symbol unknown to this feed.
        # MUST NOT raise for expected absence cases.
        ...
