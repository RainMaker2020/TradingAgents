from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as package_version
import os
import pathlib

from fastapi import APIRouter

from api.models.run import RunStatus
from api.models.settings import Settings
from api.models.system import (
    RuntimeConstraints,
    RuntimeHealth,
    RuntimeSnapshot,
    SessionStats,
)
from api.services.settings_service import load_settings
from api.store.runs_store import RunsStore

try:
    from tradingagents.default_config import DEFAULT_CONFIG
except ImportError:
    DEFAULT_CONFIG = {"results_dir": "./results"}


router = APIRouter()
_db_path = pathlib.Path(DEFAULT_CONFIG["results_dir"]) / "runs.sqlite"
_store = RunsStore(_db_path)


def _resolve_api_version() -> str:
    env_version = os.getenv("API_VERSION")
    if env_version:
        return env_version
    try:
        return package_version("tradingagents")
    except PackageNotFoundError:
        return "unknown"


def _compute_health() -> RuntimeHealth:
    api_available = True
    # sse_supported mirrors api_available: we don't probe SSE directly, but if the
    # store or settings are unavailable the SSE stream endpoint will also fail.
    sse_supported = True

    try:
        _store.list_all()
    except Exception:
        api_available = False
        sse_supported = False

    try:
        load_settings()
    except Exception:
        api_available = False
        sse_supported = False

    return RuntimeHealth(
        api_available=api_available,
        sse_supported=sse_supported,
        api_version=_resolve_api_version(),
        server_time=datetime.now(timezone.utc).isoformat(),
        runtime_mode=os.getenv("APP_ENV", "development"),
    )


@router.get("/health", response_model=RuntimeHealth)
def get_health():
    return _compute_health()


@router.get("/runtime", response_model=RuntimeSnapshot)
def get_runtime_snapshot():
    health = _compute_health()
    try:
        runs = _store.list_all() if health.api_available else []
    except Exception:
        runs = []
        health.api_available = False
        health.sse_supported = False
    latest_run = runs[0] if runs else None
    try:
        defaults = load_settings()
    except Exception:
        defaults = Settings()

    return RuntimeSnapshot(
        health=health,
        session=SessionStats(
            total_runs=len(runs),
            queued_runs=sum(1 for run in runs if run.status == RunStatus.QUEUED),
            running_runs=sum(1 for run in runs if run.status == RunStatus.RUNNING),
            complete_runs=sum(1 for run in runs if run.status == RunStatus.COMPLETE),
            error_runs=sum(1 for run in runs if run.status == RunStatus.ERROR),
            latest_run_id=latest_run.id if latest_run else None,
        ),
        constraints=RuntimeConstraints(
            min_rounds=1,
            max_rounds=5,
        ),
        defaults=defaults,
    )
