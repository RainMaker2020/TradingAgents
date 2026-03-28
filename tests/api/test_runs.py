import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app

@pytest.mark.asyncio
async def test_create_run_returns_run_id():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/runs", json={
            "ticker": "NVDA", "date": "2024-05-10"
        })
    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert body.get("mode") == "graph"

@pytest.mark.asyncio
async def test_list_runs_empty_initially():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_abort_run_returns_aborted():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a run
        create_resp = await client.post("/api/runs", json={"ticker": "NVDA", "date": "2026-03-25"})
        run_id = create_resp.json()["id"]
        # Abort it (still QUEUED)
        abort_resp = await client.post(f"/api/runs/{run_id}/abort")
    assert abort_resp.status_code == 200
    assert abort_resp.json()["status"] == "aborted"

@pytest.mark.asyncio
async def test_abort_run_noop_for_unknown_run():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/runs/nonexistent/abort")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_get_run_omits_backtest_trace_by_default():
    from api.store.shared import store as _store
    from api.models.run import RunConfig
    import json

    run = _store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    _store.set_backtest_trace(run.id, json.dumps([{"event_type": "DATA_SKIPPED"}]))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/runs/{run.id}")
    assert response.status_code == 200
    assert response.json().get("backtest_trace") is None


@pytest.mark.asyncio
async def test_get_run_include_backtest_trace_query():
    from api.store.shared import store as _store
    from api.models.run import RunConfig
    import json

    run = _store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    payload = [{"event_type": "SIGNAL_GENERATED", "symbol": "NVDA"}]
    _store.set_backtest_trace(run.id, json.dumps(payload))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/runs/{run.id}",
            params={"include_backtest_trace": "true"},
        )
    assert response.status_code == 200
    assert response.json()["backtest_trace"] == payload


@pytest.mark.asyncio
async def test_abort_run_noop_for_complete():
    from api.store.shared import store as _store
    from api.models.run import RunConfig, RunStatus
    run = _store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    _store.update_status(run.id, RunStatus.COMPLETE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/runs/{run.id}/abort")
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_op"
