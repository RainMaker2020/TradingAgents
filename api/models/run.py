from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from tradingagents.llm_clients.validators import supports_function_calling, validate_model
from tradingagents.engine.schemas.orders import FillModel as _FillModel

# Derived from FillModel enum — stays in sync automatically.
_VALID_FILL_MODELS = {m.value for m in _FillModel}


class SimulationConfigSchema(BaseModel):
    """User-facing simulation configuration accepted by the run-creation API.

    All values use human-friendly units:
      - Cash and fees in USD ($)
      - Slippage in basis points (bps)
      - max_position_pct in percent (%) — API accepts 10, engine stores 0.10.

    Normalized to engine units via SimulationConfigInput.to_simulation_config()
    in the service layer before being passed to the execution engine.

    API accepts percent; engine stores ratio.

    **Mode scope:** Fields ``stop_loss_percentage``, ``take_profit_target``,
    ``max_drawdown_limit``, and ``max_position_size`` are enforced only when
    ``RunConfig.mode == "backtest"``. Graph runs must omit them (API validation).

    Example payload::

        {
          "ticker": "AAPL",
          "date": "2024-01-02",
          "simulation_config": {
            "initial_cash": 100000,
            "slippage_bps": 5,
            "fee_per_trade": 1.0,
            "max_position_pct": 10
          }
        }
    """

    # USD fields
    initial_cash: float = Field(
        default=100_000,
        description="Starting portfolio cash in USD ($). Must be greater than 0.",
        examples=[100000],
    )
    fee_per_trade: float = Field(
        default=1.0,
        description="Flat fee in USD ($) charged per trade. Must be 0 or greater.",
        examples=[1.0],
    )

    # bps fields
    slippage_bps: float = Field(
        default=5,
        description="Slippage applied to each fill price, in basis points (bps). Must be 0 or greater.",
        examples=[5],
    )
    fee_bps: Optional[float] = Field(
        default=None,
        description=(
            "Optional percentage fee on notional, in basis points (bps). "
            "When set: total_fee = fee_per_trade + qty × price × fee_bps / 10000. "
            "Must be 0 or greater when provided."
        ),
        examples=[3.0],
    )

    # Percent field — normalized to ratio in engine
    max_position_pct: float = Field(
        default=10,
        description=(
            "Maximum position size as a percent of total equity "
            "(e.g. 10 = 10%). API accepts percent; engine stores ratio. "
            "Must be greater than 0 and at most 100."
        ),
        examples=[10],
    )
    stop_loss_percentage: Optional[float] = Field(
        default=None,
        description=(
            "Backtest only. Stop loss below average entry, as percent (e.g. 5 = 5%). "
            "Omit to disable. Not allowed when mode=graph."
        ),
        examples=[5.0],
    )
    take_profit_target: Optional[float] = Field(
        default=None,
        description=(
            "Backtest only. Take-profit above average entry, as percent. "
            "Omit to disable. Not allowed when mode=graph."
        ),
        examples=[10.0],
    )
    max_drawdown_limit: Optional[float] = Field(
        default=None,
        description=(
            "Backtest only. Max drawdown from peak equity, percent (e.g. 15 = 15%). "
            "Blocks new BUYs when exceeded. Not allowed when mode=graph."
        ),
        examples=[15.0],
    )
    max_position_size: Optional[float] = Field(
        default=None,
        description=(
            "Backtest only. Maximum shares per symbol (absolute cap). "
            "Not allowed when mode=graph."
        ),
        examples=[500.0],
    )

    # Engine pass-through fields
    fill_model: str = Field(
        default="NEXT_OPEN",
        description="Fill execution model. One of: NEXT_OPEN, SAME_CLOSE, VWAP.",
        examples=["NEXT_OPEN"],
    )
    min_confidence_threshold: float = Field(
        default=0.5,
        description=(
            "Minimum signal confidence to pass the risk gate (0.0–1.0). "
            "In backtest with LangGraphStrategyAdapter, emitted confidence is "
            "max(0.8, this value) (capped at 1.0) so it clears the gate while "
            "preserving a floor for position sizing."
        ),
        examples=[0.5],
    )
    random_seed: int = Field(
        default=42,
        description="Seed for stochastic engine components.",
        examples=[42],
    )
    calendar_timezone: str = Field(
        default="America/New_York",
        description="IANA timezone for the market calendar.",
        examples=["America/New_York"],
    )

    @field_validator("initial_cash")
    @classmethod
    def _initial_cash_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Initial Cash (USD) must be greater than 0")
        return v

    @field_validator("slippage_bps")
    @classmethod
    def _slippage_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Slippage (bps) must be 0 or greater")
        return v

    @field_validator("fee_per_trade")
    @classmethod
    def _fee_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Fee Per Trade (USD) must be 0 or greater")
        return v

    @field_validator("fee_bps")
    @classmethod
    def _fee_bps_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Fee (bps) must be 0 or greater when provided")
        return v

    @field_validator("max_position_pct")
    @classmethod
    def _max_position_in_range(cls, v: float) -> float:
        if v <= 0 or v > 100:
            raise ValueError(
                "max_position_pct (percent of equity) must be greater than 0 and at most 100"
            )
        return v

    @field_validator("stop_loss_percentage", "take_profit_target", "max_drawdown_limit")
    @classmethod
    def _optional_risk_percent_api(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if v <= 0 or v > 100:
            raise ValueError("Risk percentage fields must be between 0 and 100 when set")
        return v

    @field_validator("max_position_size")
    @classmethod
    def _optional_max_shares_api(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if v <= 0:
            raise ValueError("max_position_size must be greater than 0 when set")
        return v

    @field_validator("fill_model")
    @classmethod
    def _fill_model_valid(cls, v: str) -> str:
        upper = v.upper()
        if upper not in _VALID_FILL_MODELS:
            raise ValueError(
                f"fill_model must be one of {sorted(_VALID_FILL_MODELS)}, got '{v}'"
            )
        return upper

    @field_validator("min_confidence_threshold")
    @classmethod
    def _confidence_in_range(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("min_confidence_threshold must be between 0.0 and 1.0")
        return v

    def has_backtest_only_risk_overrides(self) -> bool:
        """True when optional fields that only apply to engine/backtest are set."""
        return (
            self.stop_loss_percentage is not None
            or self.take_profit_target is not None
            or self.max_drawdown_limit is not None
            or self.max_position_size is not None
        )


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    ABORTED = "aborted"


class RunConfig(BaseModel):
    ticker: str
    date: str  # "YYYY-MM-DD"
    llm_provider: str = "openai"
    deep_think_llm: str = "gpt-5.2"
    quick_think_llm: str = "gpt-5-mini"
    max_debate_rounds: int = Field(default=1, ge=1, le=5)
    max_risk_discuss_rounds: int = Field(default=1, ge=1, le=5)
    enabled_analysts: list[str] = Field(
        default=["market", "news", "fundamentals", "social"],
        min_length=1,
    )
    simulation_config: Optional[SimulationConfigSchema] = Field(
        default=None,
        description=(
            "Optional simulation parameters in user-friendly units. "
            "If omitted, engine defaults are used. "
            "max_position_pct is expressed as percent (10 = 10%); "
            "the engine receives the normalized ratio (0.10). "
            "Backtest-only risk keys (stop_loss_percentage, take_profit_target, "
            "max_drawdown_limit, max_position_size) must be omitted when mode=graph."
        ),
    )
    mode: Literal["graph", "backtest"] = Field(
        default="graph",
        description=(
            "'graph' runs TradingAgentsGraph (LLM multi-agent analysis, default). "
            "'backtest' runs BacktestLoop against cached CSV data using a "
            "MA-crossover strategy and the normalized simulation_config."
        ),
    )
    end_date: Optional[str] = Field(
        default=None,
        description=(
            "End date for backtest mode (YYYY-MM-DD). "
            "Defaults to date (single-day run) when omitted. "
            "Ignored in graph mode."
        ),
    )

    @model_validator(mode="after")
    def validate_llm_combo(self):
        provider = self.llm_provider.lower()
        if not validate_model(provider, self.deep_think_llm):
            raise ValueError(f"Unsupported deep_think_llm '{self.deep_think_llm}' for provider '{provider}'")
        if not validate_model(provider, self.quick_think_llm):
            raise ValueError(f"Unsupported quick_think_llm '{self.quick_think_llm}' for provider '{provider}'")

        # Analyst nodes call bind_tools() via quick_think_llm, so it must support function
        # calling. deep_think_llm is not checked here because its nodes (research_manager,
        # risk_manager) use plain invoke(), and chief_analyst uses with_structured_output()
        # which already falls back to json_mode for non-function-calling models.
        if not supports_function_calling(provider, self.quick_think_llm):
            raise ValueError(
                f"quick_think_llm '{self.quick_think_llm}' does not support function calling for provider '{provider}'"
            )
        return self

    @model_validator(mode="after")
    def validate_graph_mode_simulation_fields(self):
        """Graph runs do not execute BacktestLoop; reject misleading risk overrides."""
        if self.mode != "graph":
            return self
        sim = self.simulation_config
        if sim is None or not sim.has_backtest_only_risk_overrides():
            return self
        raise ValueError(
            "For mode='graph', simulation_config must not set backtest-only fields "
            "(stop_loss_percentage, take_profit_target, max_drawdown_limit, "
            "max_position_size). Omit them or use mode='backtest'."
        )

    @model_validator(mode="after")
    def validate_backtest_date_range(self):
        if self.mode != "backtest":
            return self
        from datetime import date as date_cls

        try:
            start = date_cls.fromisoformat(self.date)
            end = date_cls.fromisoformat(self.end_date) if self.end_date else start
        except ValueError as exc:
            raise ValueError("date and end_date must be valid YYYY-MM-DD strings") from exc
        if end < start:
            raise ValueError("end_date must be on or after date for backtest mode")
        return self


class RunSummary(BaseModel):
    id: str
    ticker: str
    date: str
    status: RunStatus
    mode: Literal["graph", "backtest"] = Field(
        default="graph",
        description=(
            "'graph' = LLM multi-agent pipeline; 'backtest' = execution engine / "
            "simulated backtest loop."
        ),
    )
    decision: Optional[Literal["BUY", "SELL", "HOLD"]] = Field(
        default=None,
        description=(
            "Graph mode: model verdict. Backtest: mirrors terminal portfolio state "
            "(BUY = open long, SELL = flat after at least one fill, HOLD = no fills); "
            "prefer backtest_metrics.terminal_exposure when present."
        ),
    )
    created_at: str


class TokenUsage(BaseModel):
    tokens_in: int = 0
    tokens_out: int = 0


class RunResult(RunSummary):
    config: Optional[RunConfig] = None
    reports: dict[str, str] = Field(default_factory=dict)
    error: Optional[str] = None
    token_usage: dict[str, TokenUsage] = Field(default_factory=dict)
    # Backtest-only: loaded only when RunsStore.get(..., include_backtest_trace=True)
    # or GET /runs/{id}?include_backtest_trace=true. Omitted from default fetches to
    # avoid large JSON payloads and parse cost on list/hot paths.
    backtest_trace: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description=(
            "Decoded backtest event trace when explicitly requested; otherwise null."
        ),
    )
