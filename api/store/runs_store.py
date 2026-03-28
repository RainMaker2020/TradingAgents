import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal, Optional

from api.models.run import RunConfig, RunResult, RunStatus, TokenUsage

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    ticker      TEXT NOT NULL,
    date        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'queued',
    decision    TEXT,
    created_at  TEXT NOT NULL,
    config      TEXT,
    reports     TEXT NOT NULL DEFAULT '{}',
    error       TEXT,
    token_usage TEXT NOT NULL DEFAULT '{}'
)
"""


class RunsStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_TABLE_SQL)
        # Migration: add token_usage column if not present (handles existing DBs)
        existing_cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(runs)")
        }
        if "token_usage" not in existing_cols:
            self._conn.execute(
                "ALTER TABLE runs ADD COLUMN token_usage TEXT NOT NULL DEFAULT '{}'"
            )
        if "backtest_trace" not in existing_cols:
            self._conn.execute(
                "ALTER TABLE runs ADD COLUMN backtest_trace TEXT"
            )
        self._conn.commit()
        self._lock = Lock()

    @staticmethod
    def _parse_backtest_trace_column(raw: str | None, run_id: str) -> list[dict[str, Any]] | None:
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "Invalid backtest_trace JSON for run %s; treating as absent", run_id
            )
            return None
        if not isinstance(parsed, list):
            logger.warning(
                "backtest_trace for run %s is not a JSON array; treating as absent", run_id
            )
            return None
        return parsed

    def _row_to_run(
        self, row: sqlite3.Row, *, include_backtest_trace: bool = False
    ) -> RunResult:
        run_id = row["id"]
        raw_trace = row["backtest_trace"] if "backtest_trace" in row.keys() else None
        if include_backtest_trace:
            backtest_trace = self._parse_backtest_trace_column(raw_trace, run_id)
        else:
            backtest_trace = None
        return RunResult(
            id=row["id"],
            ticker=row["ticker"],
            date=row["date"],
            status=RunStatus(row["status"]),
            decision=row["decision"],
            created_at=row["created_at"],
            config=RunConfig(**json.loads(row["config"])) if row["config"] else None,
            reports=json.loads(row["reports"]),
            error=row["error"],
            token_usage={
                k: TokenUsage(**v)
                for k, v in json.loads(row["token_usage"] or "{}").items()
            },
            backtest_trace=backtest_trace,
        )

    def create(self, config: RunConfig) -> RunResult:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            for _ in range(5):
                run_id = str(uuid.uuid4())[:12]
                try:
                    self._conn.execute(
                        "INSERT INTO runs (id, ticker, date, status, created_at, config)"
                        " VALUES (?, ?, ?, ?, ?, ?)",
                        (run_id, config.ticker, config.date, RunStatus.QUEUED.value,
                         now, config.model_dump_json()),
                    )
                    self._conn.commit()
                    break
                except sqlite3.IntegrityError:
                    continue
            else:
                raise RuntimeError("Failed to generate a unique run ID after 5 attempts")
        return RunResult(
            id=run_id,
            ticker=config.ticker,
            date=config.date,
            status=RunStatus.QUEUED,
            created_at=now,
            config=config,
        )

    def try_claim_run(self, run_id: str) -> bool:
        """Atomically transition a run from QUEUED or ERROR to RUNNING.

        Returns True if the claim succeeded (this caller owns the run),
        False if another caller already claimed it (status was not QUEUED/ERROR).
        Used to prevent double-pipeline execution on concurrent SSE reconnects.
        """
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE runs SET status = ? WHERE id = ? AND status IN (?, ?)",
                (RunStatus.RUNNING.value, run_id,
                 RunStatus.QUEUED.value, RunStatus.ERROR.value),
            )
            claimed = cursor.rowcount > 0
            self._conn.commit()
        return claimed

    def get(
        self, run_id: str, *, include_backtest_trace: bool = False
    ) -> Optional[RunResult]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
        return (
            self._row_to_run(row, include_backtest_trace=include_backtest_trace)
            if row
            else None
        )

    def list_all(self) -> list[RunResult]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_run(row, include_backtest_trace=False) for row in rows]

    def update_status(self, run_id: str, status: RunStatus) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET status = ? WHERE id = ?",
                (status.value, run_id),
            )
            self._conn.commit()

    def update_decision(
        self, run_id: str, decision: Literal["BUY", "SELL", "HOLD"]
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET decision = ? WHERE id = ?",
                (decision, run_id),
            )
            self._conn.commit()

    def add_report(self, run_id: str, step: str, report: str) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT reports FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row:
                reports = json.loads(row[0])
                reports[step] = report
                self._conn.execute(
                    "UPDATE runs SET reports = ? WHERE id = ?",
                    (json.dumps(reports), run_id),
                )
                self._conn.commit()

    def set_error(self, run_id: str, error: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET status = ?, error = ? WHERE id = ?",
                (RunStatus.ERROR.value, error, run_id),
            )
            self._conn.commit()

    def clear_reports(self, run_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET reports = '{}' WHERE id = ?",
                (run_id,),
            )
            self._conn.commit()

    def set_backtest_trace(self, run_id: str, trace_json: str) -> None:
        """Persist serialized BacktestEvent list (JSON array). Backtest runs only."""
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET backtest_trace = ? WHERE id = ?",
                (trace_json, run_id),
            )
            self._conn.commit()

    def clear_backtest_trace(self, run_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET backtest_trace = NULL WHERE id = ?",
                (run_id,),
            )
            self._conn.commit()

    def add_token_usage(self, run_id: str, key: str, tokens: dict) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT token_usage FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row:
                usage = json.loads(row[0] or "{}")
                usage[key] = tokens
                self._conn.execute(
                    "UPDATE runs SET token_usage = ? WHERE id = ?",
                    (json.dumps(usage), run_id),
                )
                self._conn.commit()

    def clear_token_usage(self, run_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET token_usage = '{}' WHERE id = ?",
                (run_id,),
            )
            self._conn.commit()

    def try_abort_run(self, run_id: str) -> bool:
        """Atomically transition QUEUED or RUNNING → ABORTED.

        Returns True if the transition happened, False if already terminal.
        """
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE runs SET status = ? WHERE id = ? AND status IN (?, ?)",
                (RunStatus.ABORTED.value, run_id,
                 RunStatus.QUEUED.value, RunStatus.RUNNING.value),
            )
            aborted = cursor.rowcount > 0
            self._conn.commit()
        return aborted

    def try_complete_run(self, run_id: str, decision: str) -> bool:
        """Atomically transition RUNNING → COMPLETE with decision.

        Returns False (no-op) if status is not RUNNING — prevents overwriting ABORTED.
        """
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE runs SET status = ?, decision = ? WHERE id = ? AND status = ?",
                (RunStatus.COMPLETE.value, decision, run_id, RunStatus.RUNNING.value),
            )
            completed = cursor.rowcount > 0
            self._conn.commit()
        return completed

    def try_error_run(self, run_id: str, error: str) -> bool:
        """Atomically transition RUNNING → ERROR with error message.

        Returns False (no-op) if status is not RUNNING — prevents overwriting ABORTED.
        """
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE runs SET status = ?, error = ? WHERE id = ? AND status = ?",
                (RunStatus.ERROR.value, error, run_id, RunStatus.RUNNING.value),
            )
            errored = cursor.rowcount > 0
            self._conn.commit()
        return errored
