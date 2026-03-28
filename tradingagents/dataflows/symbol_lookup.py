# tradingagents/dataflows/symbol_lookup.py
"""Resolve user ticker input to a Yahoo Finance symbol and human-readable name."""
from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf

from tradingagents.dataflows.yahoo_symbol import (
    INVALID_TICKER_HINTS,
    resolve_yahoo_ticker,
)


@dataclass(frozen=True)
class SymbolLookupResult:
    valid: bool
    query: str
    yahoo_symbol: str
    display_name: str | None
    message: str | None


def lookup_yahoo_symbol(user_input: str) -> SymbolLookupResult:
    """Validate against Yahoo Finance (yfinance). Returns canonical chart symbol."""
    raw = (user_input or "").strip()
    if not raw:
        return SymbolLookupResult(
            False, "", "", None, "Enter a ticker or symbol."
        )

    u = raw.upper()
    if u in INVALID_TICKER_HINTS:
        return SymbolLookupResult(False, raw, u, None, INVALID_TICKER_HINTS[u])

    yahoo = resolve_yahoo_ticker(raw)
    try:
        t = yf.Ticker(yahoo)
        info = t.info or {}
    except Exception as exc:  # pragma: no cover - defensive
        return SymbolLookupResult(
            False, raw, yahoo, None, f"Lookup failed: {exc}"
        )

    short = info.get("shortName") or info.get("longName")
    quote_type = info.get("quoteType")
    has_quote = bool(
        info.get("regularMarketPrice") is not None
        or info.get("previousClose") is not None
        or info.get("bid") is not None
    )

    if info and (short or has_quote or quote_type):
        sym = str(info.get("symbol") or yahoo).upper()
        label = str(short).strip() if short else sym
        return SymbolLookupResult(True, raw, sym, label, None)

    try:
        hist = t.history(period="5d")
    except Exception:
        hist = None

    if hist is not None and not hist.empty:
        label = str(short).strip() if short else yahoo.upper()
        return SymbolLookupResult(True, raw, yahoo.upper(), label, None)

    return SymbolLookupResult(
        False,
        raw,
        yahoo.upper(),
        None,
        f"Yahoo Finance returned no data for “{yahoo}”. Check the symbol or try the "
        f"full form (e.g. BTC-USD, GC=F, ^GSPC).",
    )
