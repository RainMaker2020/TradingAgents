# tradingagents/dataflows/yahoo_symbol.py
"""Map user-facing tickers to Yahoo Finance symbols for downloads and cache filenames."""
from __future__ import annotations

# Shorthand / common mistakes -> Yahoo chart symbol (yfinance)
YAHOO_CHART_ALIASES: dict[str, str] = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "XRP": "XRP-USD",
    "DOGE": "DOGE-USD",
    "LTC": "LTC-USD",
    "ADA": "ADA-USD",
    "DOT": "DOT-USD",
    "AVAX": "AVAX-USD",
    "LINK": "LINK-USD",
}

# Exchange / venue names that are not tickers (help users pick a real symbol)
INVALID_TICKER_HINTS: dict[str, str] = {
    "COMEX": "COMEX is an exchange, not a Yahoo ticker. Use a contract such as GC=F (gold) or SI=F (silver).",
    "NYSE": "NYSE is an exchange. Enter a listed symbol (e.g. AAPL), not the venue name.",
    "NASDAQ": "NASDAQ is an exchange. Enter a listed symbol (e.g. MSFT), not the venue name.",
}


def resolve_yahoo_ticker(ticker: str) -> str:
    """Return the Yahoo Finance symbol used for history download and cache file names."""
    u = ticker.strip().upper()
    return YAHOO_CHART_ALIASES.get(u, u)


def cache_filename_prefixes(ticker: str) -> list[str]:
    """Ordered unique prefixes to match ``{prefix}-YFin-data-*.csv`` in data_cache."""
    u = ticker.strip().upper()
    out: list[str] = []
    for x in (u, f"^{u}"):
        if x not in out:
            out.append(x)
    resolved = YAHOO_CHART_ALIASES.get(u, u)
    if resolved != u:
        for x in (resolved, f"^{resolved}"):
            if x not in out:
                out.append(x)
    return out


def cache_miss_hint(user_ticker: str) -> str | None:
    """Extra sentence for FileNotFoundError when no CSV exists."""
    u = user_ticker.strip().upper()
    if u in INVALID_TICKER_HINTS:
        return INVALID_TICKER_HINTS[u]
    r = resolve_yahoo_ticker(user_ticker)
    if r != u:
        return f"For Yahoo Finance, try symbol '{r}' and run analysis once to download OHLCV."
    return None
