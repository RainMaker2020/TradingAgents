from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.symbol_lookup import lookup_yahoo_symbol


def test_empty_query_invalid():
    r = lookup_yahoo_symbol("  ")
    assert not r.valid
    assert "Enter" in (r.message or "")


def test_invalid_ticker_hint_nyse():
    r = lookup_yahoo_symbol("NYSE")
    assert not r.valid
    assert "exchange" in (r.message or "").lower()


@patch("tradingagents.dataflows.symbol_lookup.yf.Ticker")
def test_valid_from_info(mock_ticker_cls):
    mock_ticker_cls.return_value.info = {
        "symbol": "AAPL",
        "shortName": "Apple Inc.",
        "quoteType": "EQUITY",
        "regularMarketPrice": 180.0,
    }
    r = lookup_yahoo_symbol("aapl")
    assert r.valid
    assert r.yahoo_symbol == "AAPL"
    assert r.display_name == "Apple Inc."


@patch("tradingagents.dataflows.symbol_lookup.yf.Ticker")
def test_valid_from_history_when_info_sparse(mock_ticker_cls):
    t = MagicMock()
    t.info = {}
    t.history.return_value = MagicMock()
    t.history.return_value.empty = False
    mock_ticker_cls.return_value = t
    r = lookup_yahoo_symbol("XYZ")
    assert r.valid
    assert r.yahoo_symbol == "XYZ"


@patch("tradingagents.dataflows.symbol_lookup.yf.Ticker")
def test_btc_alias_resolves(mock_ticker_cls):
    mock_ticker_cls.return_value.info = {
        "symbol": "BTC-USD",
        "shortName": "Bitcoin USD",
        "quoteType": "CRYPTOCURRENCY",
    }
    r = lookup_yahoo_symbol("btc")
    assert r.valid
    assert r.yahoo_symbol == "BTC-USD"


@patch("tradingagents.dataflows.symbol_lookup.yf.Ticker")
def test_invalid_when_no_data(mock_ticker_cls):
    t = MagicMock()
    t.info = {}
    t.history.return_value = MagicMock()
    t.history.return_value.empty = True
    mock_ticker_cls.return_value = t
    r = lookup_yahoo_symbol("NOTREALZZZ")
    assert not r.valid
    assert r.message
