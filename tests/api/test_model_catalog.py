import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import HTTPError, RequestException

from api.services.model_catalog_service import ModelCatalogError, get_provider_models

PATCH_TARGET = "api.services.model_catalog_service.requests.get"


def test_fetch_deepseek_models_success(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "data": [{"id": "deepseek-reasoner"}, {"id": "deepseek-chat"}]
    }
    with patch(PATCH_TARGET, return_value=mock_resp):
        models = get_provider_models("deepseek")
    assert models == ["deepseek-chat", "deepseek-reasoner"]  # sorted


def test_fetch_deepseek_missing_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    # _require_key raises before requests.get is ever called
    with pytest.raises(ModelCatalogError, match="Missing API key"):
        get_provider_models("deepseek")


def test_fetch_deepseek_http_error(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    error_response = MagicMock()
    error_response.status_code = 401
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = HTTPError(response=error_response)
    with patch(PATCH_TARGET, return_value=mock_resp):
        with pytest.raises(ModelCatalogError, match=r"Provider API error \(401\)"):
            get_provider_models("deepseek")


def test_fetch_deepseek_network_error(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    with patch(PATCH_TARGET, side_effect=RequestException("connection timeout")):
        with pytest.raises(ModelCatalogError, match="Provider API request failed"):
            get_provider_models("deepseek")
