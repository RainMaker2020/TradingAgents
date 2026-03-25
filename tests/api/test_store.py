import pytest
import sqlite3 as _sqlite3
from api.store.runs_store import RunsStore
from api.models.run import RunConfig, RunStatus


def test_create_and_get_run(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    config = RunConfig(ticker="NVDA", date="2024-05-10")
    run = store.create(config)
    assert run.id is not None
    assert run.status == RunStatus.QUEUED
    fetched = store.get(run.id)
    assert fetched.ticker == "NVDA"


def test_list_runs(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    store.create(RunConfig(ticker="NVDA", date="2024-05-10"))
    store.create(RunConfig(ticker="AAPL", date="2024-05-09"))
    runs = store.list_all()
    assert len(runs) == 2


def test_update_run_status(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2024-05-10"))
    store.update_status(run.id, RunStatus.RUNNING)
    assert store.get(run.id).status == RunStatus.RUNNING


def test_add_report(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2024-05-10"))
    store.add_report(run.id, "market_analyst:0", "bullish")
    assert store.get(run.id).reports == {"market_analyst:0": "bullish"}


def test_set_error(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2024-05-10"))
    store.set_error(run.id, "timeout")
    fetched = store.get(run.id)
    assert fetched.status == RunStatus.ERROR
    assert fetched.error == "timeout"


def test_clear_reports(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2024-05-10"))
    store.add_report(run.id, "market_analyst:0", "bullish")
    store.clear_reports(run.id)
    assert store.get(run.id).reports == {}


def test_update_decision(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2024-05-10"))
    store.update_decision(run.id, "BUY")
    assert store.get(run.id).decision == "BUY"


def test_migration_adds_token_usage_column_to_existing_db(tmp_path):
    """DB created without token_usage gets the column added on RunsStore.__init__."""
    db_path = tmp_path / "old.sqlite"
    # Create a DB without the token_usage column (simulate pre-migration state)
    conn = _sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE runs (
            id TEXT PRIMARY KEY, ticker TEXT NOT NULL, date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued', decision TEXT,
            created_at TEXT NOT NULL, config TEXT,
            reports TEXT NOT NULL DEFAULT '{}', error TEXT
        )
    """)
    conn.commit()
    conn.close()

    # Initialising the store should migrate the column
    store = RunsStore(db_path)
    cols = {
        row["name"]
        for row in store._conn.execute("PRAGMA table_info(runs)")
    }
    assert "token_usage" in cols


def test_migration_is_idempotent(tmp_path):
    """Re-initialising the store after migration does not crash."""
    db_path = tmp_path / "test.sqlite"
    RunsStore(db_path)   # first init — creates table + column
    RunsStore(db_path)   # second init — column already present, should not crash


def test_add_token_usage(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.add_token_usage(run.id, "market_analyst:0", {"tokens_in": 1200, "tokens_out": 400})
    result = store.get(run.id)
    assert "market_analyst:0" in result.token_usage
    assert result.token_usage["market_analyst:0"].tokens_in == 1200
    assert result.token_usage["market_analyst:0"].tokens_out == 400


def test_clear_token_usage(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.add_token_usage(run.id, "market_analyst:0", {"tokens_in": 1200, "tokens_out": 400})
    store.clear_token_usage(run.id)
    assert store.get(run.id).token_usage == {}


def test_clear_token_usage_does_not_affect_reports(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.add_report(run.id, "market_analyst:0", "bullish")
    store.add_token_usage(run.id, "market_analyst:0", {"tokens_in": 100, "tokens_out": 50})
    store.clear_token_usage(run.id)
    fetched = store.get(run.id)
    assert fetched.reports == {"market_analyst:0": "bullish"}
    assert fetched.token_usage == {}


def test_run_id_is_12_chars(tmp_path):
    """IDs must be 12 hex chars to reduce birthday-collision probability."""
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    assert len(run.id) == 12


def test_try_claim_run_succeeds_for_queued(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    assert store.get(run.id).status == RunStatus.QUEUED
    claimed = store.try_claim_run(run.id)
    assert claimed is True
    assert store.get(run.id).status == RunStatus.RUNNING


def test_try_claim_run_succeeds_for_error(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.set_error(run.id, "previous failure")
    claimed = store.try_claim_run(run.id)
    assert claimed is True
    assert store.get(run.id).status == RunStatus.RUNNING


def test_try_claim_run_fails_for_already_running(tmp_path):
    """Second claim attempt returns False — run is already owned."""
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    assert store.try_claim_run(run.id) is True   # first caller wins
    assert store.try_claim_run(run.id) is False  # second caller loses


def test_try_claim_run_fails_for_complete(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-23"))
    store.update_status(run.id, RunStatus.COMPLETE)
    assert store.try_claim_run(run.id) is False


def test_try_abort_run_succeeds_for_queued(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    assert store.try_abort_run(run.id) is True
    assert store.get(run.id).status == RunStatus.ABORTED

def test_try_abort_run_succeeds_for_running(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    store.update_status(run.id, RunStatus.RUNNING)
    assert store.try_abort_run(run.id) is True
    assert store.get(run.id).status == RunStatus.ABORTED

def test_try_abort_run_noop_for_complete(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    store.update_status(run.id, RunStatus.COMPLETE)
    assert store.try_abort_run(run.id) is False
    assert store.get(run.id).status == RunStatus.COMPLETE

def test_try_abort_run_noop_for_error(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    store.set_error(run.id, "boom")
    assert store.try_abort_run(run.id) is False
    assert store.get(run.id).status == RunStatus.ERROR

def test_try_abort_run_noop_for_aborted(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    store.try_abort_run(run.id)
    assert store.try_abort_run(run.id) is False  # idempotent

def test_try_complete_run_only_when_running(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    store.update_status(run.id, RunStatus.RUNNING)
    assert store.try_complete_run(run.id, "BUY") is True
    fetched = store.get(run.id)
    assert fetched.status == RunStatus.COMPLETE
    assert fetched.decision == "BUY"

def test_try_complete_run_rejected_when_aborted(tmp_path):
    """try_complete_run must not overwrite ABORTED."""
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.try_abort_run(run.id)
    assert store.try_complete_run(run.id, "BUY") is False
    assert store.get(run.id).status == RunStatus.ABORTED

def test_try_error_run_only_when_running(tmp_path):
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    store.update_status(run.id, RunStatus.RUNNING)
    assert store.try_error_run(run.id, "timeout") is True
    fetched = store.get(run.id)
    assert fetched.status == RunStatus.ERROR
    assert fetched.error == "timeout"

def test_try_error_run_rejected_when_aborted(tmp_path):
    """try_error_run must not overwrite ABORTED."""
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.try_abort_run(run.id)
    assert store.try_error_run(run.id, "timeout") is False
    assert store.get(run.id).status == RunStatus.ABORTED

def test_abort_not_overwritten_by_complete_or_error_race(tmp_path):
    """If abort wins the race, subsequent complete/error writes are silently rejected."""
    store = RunsStore(tmp_path / "test.sqlite")
    run = store.create(RunConfig(ticker="NVDA", date="2026-03-25"))
    store.update_status(run.id, RunStatus.RUNNING)
    store.try_abort_run(run.id)         # abort wins
    store.try_complete_run(run.id, "BUY")   # pipeline finalizes late
    store.try_error_run(run.id, "boom")     # exception handler fires late
    assert store.get(run.id).status == RunStatus.ABORTED  # abort status preserved
