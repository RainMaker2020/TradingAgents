# tradingagents/engine/adapters/csv_feed.py
"""DataFeed and MarketCalendar backed by the existing data_cache CSV files."""
from __future__ import annotations
import glob
import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterator, Union

import pandas as pd

from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.yahoo_symbol import cache_filename_prefixes, cache_miss_hint
from tradingagents.engine.schemas.market import Bar
from tradingagents.engine.schemas.orders import RejectionCode, RejectionReason

UTC = timezone.utc

_CACHE_CSV_RANGE = re.compile(
    r"-YFin-data-(\d{4}-\d{2}-\d{2})-(\d{4}-\d{2}-\d{2})\.csv$",
    re.IGNORECASE,
)


def _cache_csv_sort_key(path: str) -> tuple[date, int, float]:
    """Prefer latest end-date in filename; tie-break by wider span, then mtime."""
    name = os.path.basename(path)
    m = _CACHE_CSV_RANGE.search(name)
    if m:
        start = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        end = datetime.strptime(m.group(2), "%Y-%m-%d").date()
        span = (end - start).days
        return (end, span, os.path.getmtime(path))
    return (date.min, 0, os.path.getmtime(path))


def _find_csv(symbol: str) -> str | None:
    """Return the path of the best cached CSV for symbol (latest filename end-date).

    Tries the bare symbol, ``^SYMBOL`` (indices), and Yahoo aliases (e.g. BTC → BTC-USD)
    so caches created with canonical Yahoo symbols still resolve when the user types a shorthand.

    Filenames follow ``{prefix}-YFin-data-{start}-{end}.csv``. Lexicographic ``max`` on paths
    is wrong when a short-range file starts with a recent year (e.g. ``2026-02-23-...`` sorts
    after ``2011-03-28-...``) — we parse ``end`` (then span, then mtime) instead.
    """
    config = get_config()
    cache_dir = config["data_cache_dir"]
    for candidate in cache_filename_prefixes(symbol):
        pattern = os.path.join(cache_dir, f"{candidate}-YFin-data-*.csv")
        matches = glob.glob(pattern)
        if matches:
            return max(matches, key=_cache_csv_sort_key)
    return None


class CsvMarketCalendar:
    """MarketCalendar derived from the actual trading dates in the loaded CSV.

    Weekends and holidays are automatically excluded because they simply do not
    appear as rows in the yfinance data.
    """

    def __init__(self, trading_dates: frozenset[date]) -> None:
        self._dates = trading_dates
        self._sorted = sorted(trading_dates)

    def is_trading_day(self, dt: date) -> bool:
        return dt in self._dates

    def next_trading_day(self, dt: date) -> date:
        for d in self._sorted:
            if d > dt:
                return d
        return dt + timedelta(days=1)  # beyond dataset: best effort

    def previous_trading_day(self, dt: date) -> date:
        for d in reversed(self._sorted):
            if d < dt:
                return d
        return dt - timedelta(days=1)

    def is_session_open(self, dt: datetime) -> bool:
        return self.is_trading_day(dt.date())


class CsvDataFeed:
    """DataFeed backed by a cached CSV from the data_cache directory.

    Satisfies the DataFeed Protocol. On construction it loads the full CSV into
    memory so stream_bars and get_bar are pure dict lookups.

    Args:
        symbol: Ticker symbol, e.g. "AAPL".
        csv_path: Optional explicit path. If omitted, the most recent matching
                  file in data_cache is used.

    Raises:
        FileNotFoundError: if no cached file is found and csv_path is not given.
    """

    def __init__(self, symbol: str, csv_path: str | None = None) -> None:
        self._symbol = symbol.upper()
        path = csv_path or _find_csv(symbol)
        if path is None:
            extra = cache_miss_hint(symbol)
            msg = (
                f"No cached CSV found for '{symbol}'. "
                "Run a TradingAgents analysis first to populate the data cache, "
                "or pass csv_path explicitly."
            )
            if extra:
                msg = f"{msg} {extra}"
            raise FileNotFoundError(msg)

        df = pd.read_csv(path, on_bad_lines="skip")
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        for col in ("Open", "High", "Low", "Close", "Volume"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["Close", "Open", "High", "Low"])
        df = df.sort_values("Date").reset_index(drop=True)

        self._bars: dict[date, Bar] = {}
        for _, row in df.iterrows():
            bar_date: date = row["Date"].date()
            # Represent each daily bar as 21:00 UTC ≈ NYSE close (4 PM ET)
            bar_ts = datetime(
                bar_date.year, bar_date.month, bar_date.day, 21, 0, 0, tzinfo=UTC
            )
            vol = int(row["Volume"]) if pd.notna(row.get("Volume")) else 0
            self._bars[bar_date] = Bar(
                symbol=symbol.upper(),
                timestamp=bar_ts,
                open=Decimal(str(round(float(row["Open"]), 6))),
                high=Decimal(str(round(float(row["High"]), 6))),
                low=Decimal(str(round(float(row["Low"]), 6))),
                close=Decimal(str(round(float(row["Close"]), 6))),
                volume=Decimal(str(vol)),
            )

        self.calendar: CsvMarketCalendar = CsvMarketCalendar(
            frozenset(self._bars.keys())
        )

    def stream_bars(
        self, symbol: str, start: date, end: date
    ) -> Iterator[Union[Bar, RejectionReason]]:
        if symbol.upper() != self._symbol:
            yield RejectionReason(code=RejectionCode.BAR_NOT_FOUND)
            return
        current = start
        while current <= end:
            bar = self._bars.get(current)
            if bar is not None:
                yield bar
            else:
                yield RejectionReason(code=RejectionCode.DATA_UNAVAILABLE)
            current += timedelta(days=1)

    def get_bar(
        self, symbol: str, as_of: date
    ) -> Union[Bar, RejectionReason]:
        if symbol.upper() != self._symbol:
            return RejectionReason(code=RejectionCode.BAR_NOT_FOUND)
        bar = self._bars.get(as_of)
        if bar is None:
            return RejectionReason(code=RejectionCode.DATA_UNAVAILABLE)
        return bar
