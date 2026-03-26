"""Model name validators for each provider.

Only validates model names - does NOT enforce limits.
Let LLM providers use their own defaults for unspecified params.
"""

VALID_MODELS = {
    "openai": [
        # GPT-5 series
        "gpt-5.4-pro",
        "gpt-5.4",
        "gpt-5.2",
        "gpt-5.1",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        # GPT-4.1 series
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
    ],
    "anthropic": [
        # Claude 4.6 series (latest)
        "claude-opus-4-6",
        "claude-sonnet-4-6",
        # Claude 4.5 series
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
    ],
    "google": [
        # Gemini 3.1 series (preview)
        "gemini-3.1-pro-preview",
        "gemini-3.1-flash-lite-preview",
        # Gemini 3 series (preview)
        "gemini-3-flash-preview",
        # Gemini 2.5 series
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ],
    "xai": [
        # Grok 4.1 series
        "grok-4-1-fast-reasoning",
        "grok-4-1-fast-non-reasoning",
        # Grok 4 series
        "grok-4-0709",
        "grok-4-fast-reasoning",
        "grok-4-fast-non-reasoning",
    ],
    "deepseek": [
        # DeepSeek V3 + R1 family
        "deepseek-chat",
        "deepseek-reasoner",
    ],
}

# Blocklist of models that do not support function calling / tool_choice.
# Add an entry here whenever a provider releases a reasoning-only or
# restricted model that rejects the `tools` parameter at the API level.
# ollama and openrouter are intentionally absent — their model namespaces
# are open-ended and cannot be statically enumerated.
_NO_FUNCTION_CALLING_MODELS = {
    "deepseek": {"deepseek-reasoner"},
}


def validate_model(provider: str, model: str) -> bool:
    """Check if model name is valid for the given provider.

    For ollama, openrouter - any model is accepted.
    """
    provider_lower = provider.lower()

    if provider_lower in ("ollama", "openrouter"):
        return True

    if provider_lower not in VALID_MODELS:
        return True

    return model in VALID_MODELS[provider_lower]


def supports_function_calling(provider: str, model: str) -> bool:
    """Return whether provider/model supports tool/function calling."""
    provider_lower = provider.lower()
    blocked = _NO_FUNCTION_CALLING_MODELS.get(provider_lower, set())
    return model not in blocked


def structured_output_method(provider: str, model: str) -> str:
    """Return safe default method for with_structured_output."""
    if not supports_function_calling(provider, model):
        return "json_mode"
    return "function_calling"
