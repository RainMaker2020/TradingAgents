import pytest
from api.models.run import RunConfig, RunSummary, RunStatus
from api.models.settings import Settings


def test_run_config_defaults():
    config = RunConfig(ticker="NVDA", date="2024-05-10")
    assert config.llm_provider == "openai"
    assert config.max_debate_rounds == 1


def test_run_summary_has_decision():
    summary = RunSummary(
        id="abc123", ticker="NVDA", date="2024-05-10",
        status=RunStatus.COMPLETE, decision="BUY", created_at="2026-03-23T09:00:00"
    )
    assert summary.decision == "BUY"


def test_settings_defaults():
    s = Settings()
    assert s.deep_think_llm == "gpt-5.2"
    assert s.max_debate_rounds == 1


def test_run_config_rejects_invalid_quick_model_for_provider():
    with pytest.raises(ValueError, match="Unsupported quick_think_llm"):
        RunConfig(
            ticker="NVDA",
            date="2024-05-10",
            llm_provider="deepseek",
            deep_think_llm="deepseek-reasoner",
            quick_think_llm="gpt-5-mini",
        )


def test_run_config_rejects_non_function_calling_quick_model():
    with pytest.raises(ValueError, match="does not support function calling"):
        RunConfig(
            ticker="NVDA",
            date="2024-05-10",
            llm_provider="deepseek",
            deep_think_llm="deepseek-chat",
            quick_think_llm="deepseek-reasoner",
        )
