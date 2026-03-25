from pydantic import BaseModel
from api.models.settings import Settings


class RuntimeHealth(BaseModel):
    api_available: bool
    sse_supported: bool
    api_version: str
    server_time: str
    runtime_mode: str


class SessionStats(BaseModel):
    total_runs: int
    queued_runs: int
    running_runs: int
    complete_runs: int
    error_runs: int
    latest_run_id: str | None = None


class RuntimeConstraints(BaseModel):
    min_rounds: int
    max_rounds: int


class RuntimeSnapshot(BaseModel):
    health: RuntimeHealth
    session: SessionStats
    constraints: RuntimeConstraints
    defaults: Settings


class ProviderModels(BaseModel):
    provider: str
    models: list[str]
    error: str | None = None
