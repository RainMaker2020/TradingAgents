"""Extra tests: no raw CSV dump patterns, % vs prior, cache reuse, mtime as-of."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from tradingagents.dataflows import y_finance

_YFIN_CSV_HEADER_SUBSTR = ",Open,High,Low,Close,Adj Close,Volume"


def test_returned_text_no_repeated_csv_header_pattern(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        y_finance,
        "get_config",
        lambda: {"data_cache_dir": str(tmp_path)},
    )
    cache_file = tmp_path / "AAPL-YFin-data-2024-01-01-2024-01-03.csv"
    cache_file.write_text(
        "Date,Open,High,Low,Close,Volume\n2024-01-02,100,101,99,100.5,123\n",
        encoding="utf-8",
    )

    class _NeverCalledTicker:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("Ticker() should not be called on cache hit")

    monkeypatch.setattr(y_finance.yf, "Ticker", _NeverCalledTicker)

    out = y_finance.get_YFin_data_online("AAPL", "2024-01-01", "2024-01-03")
    assert out.count("Date,Open,High,Low,Close") == 0
    assert _YFIN_CSV_HEADER_SUBSTR not in out


def test_percent_vs_prior_close_in_last_rows(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        y_finance,
        "get_config",
        lambda: {"data_cache_dir": str(tmp_path)},
    )

    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    closes = [100.0, 100.5, 101.0]

    class _FakeTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        def history(self, start: str, end: str):
            return pd.DataFrame(
                {
                    "Open": closes,
                    "High": [c + 1 for c in closes],
                    "Low": [c - 1 for c in closes],
                    "Close": closes,
                    "Adj Close": closes,
                    "Volume": [100, 200, 300],
                },
                index=idx,
            )

    monkeypatch.setattr(y_finance.yf, "Ticker", _FakeTicker)

    out = y_finance.get_YFin_data_online("AAPL", "2024-01-01", "2024-01-05")
    assert "0.50%" in out


def test_second_call_reuses_cache_no_second_fetch(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        y_finance,
        "get_config",
        lambda: {"data_cache_dir": str(tmp_path)},
    )

    idx = pd.to_datetime(["2024-01-02"])
    calls = {"n": 0}

    class _FakeTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        def history(self, start: str, end: str):
            calls["n"] += 1
            return pd.DataFrame(
                {
                    "Open": [10.0],
                    "High": [11.0],
                    "Low": [9.0],
                    "Close": [10.5],
                    "Adj Close": [10.5],
                    "Volume": [50],
                },
                index=idx,
            )

    monkeypatch.setattr(y_finance.yf, "Ticker", _FakeTicker)

    y_finance.get_YFin_data_online("MSFT", "2024-01-01", "2024-01-03")
    assert calls["n"] == 1
    out2 = y_finance.get_YFin_data_online("MSFT", "2024-01-01", "2024-01-03")
    assert calls["n"] == 1
    assert "# Data source: cache" in out2


def test_cache_hit_as_of_matches_file_mtime(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        y_finance,
        "get_config",
        lambda: {"data_cache_dir": str(tmp_path)},
    )
    cache_file = tmp_path / "AAPL-YFin-data-2024-01-01-2024-01-03.csv"
    cache_file.write_text(
        "Date,Open,High,Low,Close,Volume\n2024-01-02,1,2,1,1.5,1\n",
        encoding="utf-8",
    )
    mtime = 1_700_000_000
    import os

    os.utime(cache_file, (mtime, mtime))

    class _NeverCalledTicker:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("Ticker() should not be called on cache hit")

    monkeypatch.setattr(y_finance.yf, "Ticker", _NeverCalledTicker)

    out = y_finance.get_YFin_data_online("AAPL", "2024-01-01", "2024-01-03")
    expected = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    assert f"# As of: {expected}" in out
