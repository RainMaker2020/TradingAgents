import pytest
from unittest.mock import patch, MagicMock
from tradingagents.llm_clients.openai_client import OpenAIClient


PATCH_TARGET = "tradingagents.llm_clients.openai_client.NormalizedChatOpenAI"


def _get_call_kwargs(mock_cls):
    """Return the keyword arguments from the most recent NormalizedChatOpenAI call."""
    assert mock_cls.call_count == 1, "Expected exactly one call to NormalizedChatOpenAI"
    return mock_cls.call_args.kwargs


def test_deepseek_base_url():
    client = OpenAIClient("deepseek-chat", provider="deepseek")
    with patch(PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert _get_call_kwargs(mock_cls)["base_url"] == "https://api.deepseek.com/v1"


def test_deepseek_api_key_from_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    client = OpenAIClient("deepseek-chat", provider="deepseek")
    with patch(PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert _get_call_kwargs(mock_cls)["api_key"] == "sk-test-deepseek"


def test_deepseek_missing_key_omits_api_key_kwarg(monkeypatch):
    # When DEEPSEEK_API_KEY is absent, api_key must NOT appear in kwargs.
    # LangChain will then fall back to its own env resolution (OPENAI_API_KEY etc).
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = OpenAIClient("deepseek-chat", provider="deepseek")
    with patch(PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert "api_key" not in _get_call_kwargs(mock_cls)


def test_deepseek_no_responses_api():
    # DeepSeek uses Chat Completions, not the Responses API. The key must be absent.
    client = OpenAIClient("deepseek-chat", provider="deepseek")
    with patch(PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert "use_responses_api" not in _get_call_kwargs(mock_cls)


def test_openai_uses_responses_api():
    # Regression guard: native OpenAI must still set use_responses_api=True.
    client = OpenAIClient("gpt-5.2", provider="openai")
    with patch(PATCH_TARGET) as mock_cls:
        mock_cls.return_value = MagicMock()
        client.get_llm()
    assert _get_call_kwargs(mock_cls).get("use_responses_api") is True
