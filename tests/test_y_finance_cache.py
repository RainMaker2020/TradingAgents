from __future__ import annotations

from pathlib import Path

import pandas as pd

from tradingagents.dataflows import y_finance

_YFIN_CSV_HEADER_SUBSTR = ",Open,High,Low,Close,Adj Close,Volume"


def test_get_yfin_data_online_uses_cache_when_file_exists(monkeypatch, tmp_path: Path):
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
    assert "# Data source: cache" in out
    assert "# Total records: 1" in out
    assert "# As of:" in out
    assert _YFIN_CSV_HEADER_SUBSTR not in out
    assert "| 2024-01-02 |" in out


def test_get_yfin_data_online_writes_cache_on_miss(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        y_finance,
        "get_config",
        lambda: {"data_cache_dir": str(tmp_path)},
    )

    class _FakeTicker:
        def __init__(self, symbol: str):
            self.symbol = symbol

        def history(self, start: str, end: str):
            idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
            return pd.DataFrame(
                {
                    "Open": [100.0, 101.0],
                    "High": [101.0, 102.0],
                    "Low": [99.0, 100.0],
                    "Close": [100.5, 101.5],
                    "Adj Close": [100.5, 101.5],
                    "Volume": [123, 456],
                },
                index=idx,
            )

    monkeypatch.setattr(y_finance.yf, "Ticker", _FakeTicker)

    out = y_finance.get_YFin_data_online("AAPL", "2024-01-01", "2024-01-03")
    assert "# Stock data for AAPL from 2024-01-01 to 2024-01-03" in out
    assert "# Total records: 2" in out
    assert "# Data source: online" in out
    assert "# As of:" in out
    assert _YFIN_CSV_HEADER_SUBSTR not in out

    cache_file = tmp_path / "AAPL-YFin-data-2024-01-01-2024-01-03.csv"
    assert cache_file.exists()
    cached_text = cache_file.read_text(encoding="utf-8")
    assert _YFIN_CSV_HEADER_SUBSTR in cached_text
