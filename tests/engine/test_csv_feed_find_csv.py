from __future__ import annotations

from pathlib import Path

import pytest

from tradingagents.engine.adapters import csv_feed


@pytest.fixture
def cache_dir(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(
        csv_feed,
        "get_config",
        lambda: {"data_cache_dir": str(tmp_path)},
    )
    return tmp_path


def test_find_csv_prefers_latest_filename_end_date_not_lex_order(cache_dir: Path) -> None:
    """Short-range files starting with a recent year must not beat long-history CSVs."""
    (cache_dir / "AAPL-YFin-data-2011-03-28-2026-03-28.csv").write_text("", encoding="utf-8")
    (cache_dir / "AAPL-YFin-data-2026-02-23-2026-03-25.csv").write_text("", encoding="utf-8")
    chosen = csv_feed._find_csv("AAPL")
    assert chosen is not None
    assert chosen.endswith("AAPL-YFin-data-2011-03-28-2026-03-28.csv")


def test_find_csv_same_end_prefers_wider_span(cache_dir: Path) -> None:
    (cache_dir / "AAPL-YFin-data-2026-03-01-2026-03-28.csv").write_text("", encoding="utf-8")
    (cache_dir / "AAPL-YFin-data-2010-01-01-2026-03-28.csv").write_text("", encoding="utf-8")
    chosen = csv_feed._find_csv("AAPL")
    assert chosen is not None
    assert chosen.endswith("AAPL-YFin-data-2010-01-01-2026-03-28.csv")
