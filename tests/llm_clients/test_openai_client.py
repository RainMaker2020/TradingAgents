import pytest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel

from tradingagents.llm_clients.openai_client import (
    OpenAIClient,
    NormalizedChatOpenAI,
    OpenAICompatibleChat,
)

# Native OpenAI path returns NormalizedChatOpenAI
OPENAI_PATCH_TARGET = "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI"

# All other providers (DeepSeek, xAI, OpenRouter, Ollama) return OpenAICompatibleChat
COMPATIBLE_PATCH_TARGET = "tradingagents.llm_clients.openai_client.OpenAICompatibleChat"


def _get_call_kwargs(mock_cls):
    """Return the keyword arguments from the most recent constructor call."""
    assert mock_cls.call_count == 1, f"Expected exactly one call, got {mock_cls.call_count}"
    return mock_cls.call_args.kwargs


# ---------------------------------------------------------------------------
# DeepSeek — uses OpenAICompatibleChat
# ---------------------------------------------------------------------------

def test_deepseek_base_url():
    client = OpenAIClient("deepseek-chat", provider="deepseek")
    with patch(COMPATIBLE_PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert _get_call_kwargs(mock_cls)["base_url"] == "https://api.deepseek.com/v1"


def test_deepseek_api_key_from_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    client = OpenAIClient("deepseek-chat", provider="deepseek")
    with patch(COMPATIBLE_PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert _get_call_kwargs(mock_cls)["api_key"] == "sk-test-deepseek"


def test_deepseek_missing_key_omits_api_key_kwarg(monkeypatch):
    # When DEEPSEEK_API_KEY is absent, api_key must NOT appear in kwargs.
    # LangChain will then fall back to its own env resolution (OPENAI_API_KEY etc).
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = OpenAIClient("deepseek-chat", provider="deepseek")
    with patch(COMPATIBLE_PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert "api_key" not in _get_call_kwargs(mock_cls)


def test_deepseek_no_responses_api():
    # DeepSeek uses Chat Completions, not the Responses API. The key must be absent.
    client = OpenAIClient("deepseek-chat", provider="deepseek")
    with patch(COMPATIBLE_PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert "use_responses_api" not in _get_call_kwargs(mock_cls)


def test_deepseek_returns_openai_compatible_chat_instance():
    # get_llm() must return an OpenAICompatibleChat for DeepSeek, not NormalizedChatOpenAI.
    client = OpenAIClient("deepseek-chat", provider="deepseek")
    with patch(COMPATIBLE_PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock(spec=OpenAICompatibleChat)
        llm = client.get_llm()
    assert llm is mock_cls.return_value


# ---------------------------------------------------------------------------
# OpenAI — uses NormalizedChatOpenAI (intentionally NOT OpenAICompatibleChat)
# ---------------------------------------------------------------------------

def test_openai_uses_responses_api():
    # Regression guard: native OpenAI must still set use_responses_api=True.
    # Note: OpenAI path explicitly instantiates NormalizedChatOpenAI, not OpenAICompatibleChat.
    client = OpenAIClient("gpt-5.2", provider="openai")
    with patch(OPENAI_PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert _get_call_kwargs(mock_cls).get("use_responses_api") is True


def test_openai_returns_normalized_chat_instance():
    # Native OpenAI must NOT return OpenAICompatibleChat.
    client = OpenAIClient("gpt-5.2", provider="openai")
    with patch(OPENAI_PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock(spec=NormalizedChatOpenAI)
        llm = client.get_llm()
    assert llm is mock_cls.return_value


# ---------------------------------------------------------------------------
# OpenAICompatibleChat.with_structured_output — core behavior of the fix
# ---------------------------------------------------------------------------

class _Schema(BaseModel):
    value: str


def test_compatible_chat_defaults_method_to_function_calling():
    # Core fix: with_structured_output must default to function_calling so that
    # providers like DeepSeek never receive response_format=json_schema.
    instance = OpenAICompatibleChat(
        model="deepseek-chat", base_url="https://api.deepseek.com/v1", api_key="fake"
    )
    with patch.object(NormalizedChatOpenAI, "with_structured_output") as mock_wso:
        mock_wso.return_value = MagicMock()
        instance.with_structured_output(_Schema)
    assert mock_wso.call_args.kwargs.get("method") == "function_calling"


def test_compatible_chat_respects_explicit_method_override():
    # Callers can still override the method when the provider supports json_mode.
    instance = OpenAICompatibleChat(
        model="deepseek-chat", base_url="https://api.deepseek.com/v1", api_key="fake"
    )
    with patch.object(NormalizedChatOpenAI, "with_structured_output") as mock_wso:
        mock_wso.return_value = MagicMock()
        instance.with_structured_output(_Schema, method="json_mode")
    assert mock_wso.call_args.kwargs.get("method") == "json_mode"


def test_compatible_chat_forwards_include_raw():
    instance = OpenAICompatibleChat(
        model="deepseek-chat", base_url="https://api.deepseek.com/v1", api_key="fake"
    )
    with patch.object(NormalizedChatOpenAI, "with_structured_output") as mock_wso:
        mock_wso.return_value = MagicMock()
        instance.with_structured_output(_Schema, include_raw=True)
    assert mock_wso.call_args.kwargs.get("include_raw") is True


# ---------------------------------------------------------------------------
# Non-OpenAI providers all return OpenAICompatibleChat
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provider,expected_base_url", [
    ("xai", "https://api.x.ai/v1"),
    ("openrouter", "https://openrouter.ai/api/v1"),
    ("ollama", "http://localhost:11434/v1"),
])
def test_compatible_providers_return_openai_compatible_chat(provider, expected_base_url, monkeypatch):
    # All non-OpenAI providers must get OpenAICompatibleChat so they inherit
    # the function_calling default for with_structured_output.
    monkeypatch.setenv("XAI_API_KEY", "fake-xai")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter")
    client = OpenAIClient("some-model", provider=provider)
    with patch(COMPATIBLE_PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock(spec=OpenAICompatibleChat)
        llm = client.get_llm()
    assert llm is mock_cls.return_value
    assert _get_call_kwargs(mock_cls)["base_url"] == expected_base_url
