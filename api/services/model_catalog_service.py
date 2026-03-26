from __future__ import annotations

import os
from typing import Callable

import requests


class ModelCatalogError(Exception):
    """Raised when remote model lookup fails."""


def _require_key(*env_vars: str) -> str:
    for env_var in env_vars:
        value = os.getenv(env_var, "").strip()
        if value:
            return value
    raise ModelCatalogError(f"Missing API key: set one of {', '.join(env_vars)}")


def _fetch_openai_models() -> list[str]:
    api_key = _require_key("OPENAI_API_KEY")
    response = requests.get(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    models = [item.get("id", "") for item in payload.get("data", []) if item.get("id")]
    return sorted(set(models))


def _fetch_anthropic_models() -> list[str]:
    api_key = _require_key("ANTHROPIC_API_KEY")
    response = requests.get(
        "https://api.anthropic.com/v1/models",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    models = [item.get("id", "") for item in payload.get("data", []) if item.get("id")]
    return sorted(set(models))


def _fetch_google_models() -> list[str]:
    api_key = _require_key("GOOGLE_API_KEY", "GEMINI_API_KEY")
    response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": api_key},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    models: list[str] = []
    for item in payload.get("models", []):
        model_name = item.get("name", "")
        if not model_name:
            continue
        models.append(model_name.removeprefix("models/"))
    return sorted(set(models))


def _fetch_deepseek_models() -> list[str]:
    api_key = _require_key("DEEPSEEK_API_KEY")
    response = requests.get(
        "https://api.deepseek.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    models = [item.get("id", "") for item in payload.get("data", []) if item.get("id")]
    return sorted(set(models))


_FETCHERS: dict[str, Callable[[], list[str]]] = {
    "openai": _fetch_openai_models,
    "anthropic": _fetch_anthropic_models,
    "google": _fetch_google_models,
    "deepseek": _fetch_deepseek_models,
}


def get_provider_models(provider: str) -> list[str]:
    normalized = provider.strip().lower()
    if normalized not in _FETCHERS:
        raise ModelCatalogError(f"Unsupported provider: {provider}")

    try:
        return _FETCHERS[normalized]()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise ModelCatalogError(f"Provider API error ({status})") from exc
    except requests.RequestException as exc:
        raise ModelCatalogError("Provider API request failed") from exc
