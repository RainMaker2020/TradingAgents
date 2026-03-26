import pytest
from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.llm_clients.openai_client import OpenAIClient
from tradingagents.llm_clients.anthropic_client import AnthropicClient
from tradingagents.llm_clients.google_client import GoogleClient


def test_deepseek_returns_openai_client():
    client = create_llm_client("deepseek", "deepseek-chat")
    assert isinstance(client, OpenAIClient)


def test_deepseek_case_insensitive():
    # Regression guard: factory calls provider.lower() — this locks that in.
    client = create_llm_client("DeepSeek", "deepseek-chat")
    assert isinstance(client, OpenAIClient)


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm_client("unknown", "some-model")


@pytest.mark.parametrize("provider,expected_class", [
    ("openai",     OpenAIClient),
    ("anthropic",  AnthropicClient),
    ("google",     GoogleClient),
    ("deepseek",   OpenAIClient),
    ("xai",        OpenAIClient),
    ("ollama",     OpenAIClient),
    ("openrouter", OpenAIClient),
])
def test_all_providers_return_correct_client_type(provider, expected_class):
    client = create_llm_client(provider, "some-model")
    assert isinstance(client, expected_class)
