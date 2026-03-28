import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from api.models.run import RunConfig, RunResult, RunSummary
from api.services.run_service import RunService
from api.store.shared import store as _store

router = APIRouter()
_service = RunService(_store)


@router.post("", response_model=RunSummary)
def create_run(config: RunConfig):
    run = _store.create(config)
    return run


@router.get("", response_model=list[RunSummary])
def list_runs():
    return _store.list_all()


@router.get("/{run_id}", response_model=RunResult)
def get_run(
    run_id: str,
    include_backtest_trace: bool = Query(
        False,
        description="When true, include and parse the stored backtest event trace (can be large).",
    ),
):
    run = _store.get(run_id, include_backtest_trace=include_backtest_trace)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/abort")
def abort_run(run_id: str):
    run = _store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    aborted = _service.abort_run(run_id)
    return {"status": "aborted" if aborted else "no_op"}


@router.get("/{run_id}/stream")
def stream_run(run_id: str):
    run = _store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    def event_generator():
        for event in _service.stream_events(run_id):
            data = json.dumps(event["data"])
            yield f"event: {event['event']}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
