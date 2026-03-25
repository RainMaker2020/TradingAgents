from fastapi.testclient import TestClient

from api.main import app
from api.routers import system as system_router


def test_system_health_returns_runtime_fields():
    client = TestClient(app)
    response = client.get("/api/system/health")

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "api_available",
        "sse_supported",
        "api_version",
        "server_time",
        "runtime_mode",
    }
    assert isinstance(data["api_available"], bool)
    assert isinstance(data["sse_supported"], bool)


def test_runtime_snapshot_increments_after_run_creation():
    client = TestClient(app)
    before = client.get("/api/system/runtime").json()

    create_res = client.post(
        "/api/runs",
        json={"ticker": "AAPL", "date": "2026-03-25"},
    )
    assert create_res.status_code == 200

    after = client.get("/api/system/runtime").json()

    assert after["session"]["total_runs"] >= before["session"]["total_runs"] + 1
    assert after["constraints"]["min_rounds"] == 1
    assert after["constraints"]["max_rounds"] == 5
    assert "llm_provider" in after["defaults"]


def test_system_health_reports_down_when_store_fails(monkeypatch):
    def boom():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(system_router._store, "list_all", boom)
    client = TestClient(app)

    health_res = client.get("/api/system/health")
    runtime_res = client.get("/api/system/runtime")

    assert health_res.status_code == 200
    health = health_res.json()
    assert health["api_available"] is False
    assert health["sse_supported"] is False

    assert runtime_res.status_code == 200
    runtime = runtime_res.json()
    assert runtime["session"]["total_runs"] == 0
    assert runtime["health"]["api_available"] is False


def test_models_deepseek_success(monkeypatch):
    monkeypatch.setattr(
        system_router, "get_provider_models",
        lambda provider: ["deepseek-chat", "deepseek-reasoner"],
    )
    client = TestClient(app)
    response = client.get("/api/system/models/deepseek")

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "deepseek"
    assert data["models"] == ["deepseek-chat", "deepseek-reasoner"]
    assert data["error"] is None


def test_models_deepseek_catalog_error(monkeypatch):
    from api.services.model_catalog_service import ModelCatalogError

    def _raise(provider):
        raise ModelCatalogError("Missing API key: set one of DEEPSEEK_API_KEY")

    monkeypatch.setattr(system_router, "get_provider_models", _raise)
    client = TestClient(app)
    response = client.get("/api/system/models/deepseek")

    assert response.status_code == 200  # graceful — never 5xx
    data = response.json()
    assert data["provider"] == "deepseek"
    assert data["models"] == []
    assert data["error"] is not None
    assert "Missing API key" in data["error"]
