"""SQLite-backed signal decision cache for engine strategy adapters."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SignalDecisionCache:
    """Read-through cache for per-(symbol, date, config) strategy decisions."""

    def __init__(self, db_path: Path, enabled: bool = True) -> None:
        self._db_path = db_path
        self._enabled = enabled
        self._conn: sqlite3.Connection | None = None
        self._stats = {
            "read_errors": 0,
            "write_errors": 0,
        }
        if self._enabled:
            self._connect_and_init()

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    @staticmethod
    def build_cache_key(key_payload: dict[str, Any]) -> tuple[str, str]:
        key_json = json.dumps(key_payload, sort_keys=True, separators=(",", ":"))
        key_hash = hashlib.sha256(key_json.encode("utf-8")).hexdigest()
        return key_hash, key_json

    def get(self, key_payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self._enabled or self._conn is None:
            return None
        try:
            key_hash, _ = self.build_cache_key(key_payload)
            row = self._conn.execute(
                "SELECT value_json FROM signal_decisions WHERE cache_key = ?",
                (key_hash,),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row[0])
        except Exception:
            self._stats["read_errors"] += 1
            return None

    def set(self, key_payload: dict[str, Any], value_payload: dict[str, Any]) -> None:
        if not self._enabled or self._conn is None:
            return
        try:
            key_hash, key_json = self.build_cache_key(key_payload)
            value_json = json.dumps(value_payload, sort_keys=True, separators=(",", ":"))
            created_at = datetime.now(timezone.utc).isoformat()
            self._conn.execute(
                """
                INSERT OR REPLACE INTO signal_decisions(cache_key, key_json, value_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (key_hash, key_json, value_json, created_at),
            )
            self._conn.commit()
        except Exception:
            self._stats["write_errors"] += 1

    def close(self) -> None:
        if self._conn is None:
            return
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = None

    def _connect_and_init(self) -> None:
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute("PRAGMA busy_timeout=5000;")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_decisions (
                    cache_key TEXT PRIMARY KEY,
                    key_json TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_signal_decisions_created ON signal_decisions(created_at)"
            )
            self._conn.commit()
        except Exception:
            self._stats["write_errors"] += 1
            self._conn = None
