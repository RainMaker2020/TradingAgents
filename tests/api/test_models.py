import pytest
from api.models.run import RunConfig, RunSummary, RunStatus, SimulationConfigSchema
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
    assert s.execution_mode == "graph"
    assert s.profile_preset is None


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


def test_graph_mode_rejects_stop_loss_in_simulation_config():
    with pytest.raises(ValueError, match="backtest-only"):
        RunConfig(
            ticker="NVDA",
            date="2024-05-10",
            mode="graph",
            simulation_config=SimulationConfigSchema(stop_loss_percentage=5.0),
        )


def test_graph_mode_allows_simulation_config_without_backtest_risk_fields():
    cfg = RunConfig(
        ticker="NVDA",
        date="2024-05-10",
        mode="graph",
        simulation_config=SimulationConfigSchema(max_position_pct=15),
    )
    assert cfg.simulation_config is not None
    assert cfg.simulation_config.max_position_pct == 15


def test_backtest_mode_allows_backtest_risk_fields():
    cfg = RunConfig(
        ticker="NVDA",
        date="2024-05-10",
        mode="backtest",
        simulation_config=SimulationConfigSchema(
            stop_loss_percentage=5.0,
            max_drawdown_limit=10.0,
        ),
    )
    assert cfg.simulation_config.stop_loss_percentage == 5.0


def test_backtest_rejects_end_date_before_start():
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="end_date must be on or after"):
        RunConfig(
            ticker="NVDA",
            date="2024-06-10",
            mode="backtest",
            end_date="2024-06-01",
        )


def test_simulation_config_fill_model_values_match_engine_enum():
    from tradingagents.engine.schemas.orders import FillModel

    for m in FillModel:
        s = SimulationConfigSchema(fill_model=m.value)
        assert s.fill_model == m.value
