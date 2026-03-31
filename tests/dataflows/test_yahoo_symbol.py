"""Tests for Yahoo ticker normalization used by cache and downloads."""
from tradingagents.dataflows.yahoo_symbol import (
    cache_filename_prefixes,
    cache_miss_hint,
    resolve_yahoo_ticker,
)


def test_resolve_btc_to_btc_usd() -> None:
    assert resolve_yahoo_ticker("btc") == "BTC-USD"
    assert resolve_yahoo_ticker("BTC-USD") == "BTC-USD"


def test_cache_prefixes_include_alias() -> None:
    p = cache_filename_prefixes("btc")
    assert p[0] == "BTC"
    assert "BTC-USD" in p


def test_comex_hint() -> None:
    h = cache_miss_hint("COMEX")
    assert h is not None
    assert "GC=F" in h


def test_btc_hint_suggests_canonical() -> None:
    h = cache_miss_hint("BTC")
    assert h is not None
    assert "BTC-USD" in h
