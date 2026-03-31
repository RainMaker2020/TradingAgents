from __future__ import annotations

from pydantic import BaseModel, Field


class SymbolResolveResponse(BaseModel):
    valid: bool
    query: str = Field(description="Original user input")
    yahoo_symbol: str = Field(description="Canonical Yahoo Finance symbol for data/cache")
    display_name: str | None = Field(
        default=None,
        description="Short or long name from Yahoo when available",
    )
    message: str | None = Field(
        default=None,
        description="Error or hint when valid is false",
    )
