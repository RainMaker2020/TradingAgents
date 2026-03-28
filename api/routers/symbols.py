from __future__ import annotations

from fastapi import APIRouter, Query

from api.models.symbol_resolve import SymbolResolveResponse
from tradingagents.dataflows.symbol_lookup import lookup_yahoo_symbol

router = APIRouter()


@router.get("/resolve", response_model=SymbolResolveResponse)
def resolve_symbol(q: str = Query(..., min_length=1, max_length=64)):
    """Resolve and validate a ticker via Yahoo Finance before starting a run."""
    r = lookup_yahoo_symbol(q)
    return SymbolResolveResponse(
        valid=r.valid,
        query=r.query,
        yahoo_symbol=r.yahoo_symbol,
        display_name=r.display_name,
        message=r.message,
    )
