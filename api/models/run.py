from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

from tradingagents.llm_clients.validators import supports_function_calling, validate_model


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


class RunSummary(BaseModel):
    id: str
    ticker: str
    date: str
    status: RunStatus
    decision: Optional[Literal["BUY", "SELL", "HOLD"]] = None
    created_at: str


class TokenUsage(BaseModel):
    tokens_in: int = 0
    tokens_out: int = 0


class RunResult(RunSummary):
    config: Optional[RunConfig] = None
    reports: dict[str, str] = Field(default_factory=dict)
    error: Optional[str] = None
    token_usage: dict[str, TokenUsage] = Field(default_factory=dict)
