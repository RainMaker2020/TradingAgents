"""Unit tests for backtest headline formatting (Layer 2)."""
from datetime import date

from api.models.backtest import BacktestMetricsPayload, format_backtest_headline


def test_format_backtest_headline_range_and_return():
    payload = BacktestMetricsPayload(
        initial_cash=100_000.0,
        final_equity=96_500.0,
        total_return_pct=-3.5,
        unrealized_pnl=1_500.0,
        realized_pnl=200.0,
        total_fees_paid=5.0,
        fill_count=3,
        max_drawdown_pct=None,
        as_of=None,
        positions={"AAPL": "10"},
    )
    h = format_backtest_headline("aapl", date(2024, 1, 2), date(2024, 1, 10), payload)
    assert "AAPL" in h
    assert "2024-01-02 → 2024-01-10" in h
    assert "3 fills" in h
    assert "$96,500.00" in h
    assert "-3.50%" in h


def test_format_backtest_headline_single_day_na_return():
    payload = BacktestMetricsPayload(
        initial_cash=0.0,
        final_equity=0.0,
        total_return_pct=None,
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        total_fees_paid=0.0,
        fill_count=0,
        max_drawdown_pct=None,
        as_of=None,
        positions={},
    )
    d = date(2024, 6, 1)
    h = format_backtest_headline("x", d, d, payload)
    assert "2024-06-01" in h
    assert "→" not in h
    assert "N/A%" in h
