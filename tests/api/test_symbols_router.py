from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@patch("api.routers.symbols.lookup_yahoo_symbol")
def test_resolve_endpoint(mock_lookup, client):
    from tradingagents.dataflows.symbol_lookup import SymbolLookupResult

    mock_lookup.return_value = SymbolLookupResult(
        True, "NVDA", "NVDA", "NVIDIA Corporation", None
    )
    r = client.get("/api/symbols/resolve", params={"q": "NVDA"})
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is True
    assert data["yahoo_symbol"] == "NVDA"
    assert data["display_name"] == "NVIDIA Corporation"
