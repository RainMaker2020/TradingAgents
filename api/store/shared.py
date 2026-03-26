"""Single shared RunsStore instance for the entire API process.

Both the runs router and the system router use this module so they share
one SQLite connection and one threading.Lock, avoiding dual-instance
coordination issues.
"""
import pathlib

try:
    from tradingagents.default_config import DEFAULT_CONFIG
except ImportError:
    DEFAULT_CONFIG = {"results_dir": "./results"}

from api.store.runs_store import RunsStore

_db_path = pathlib.Path(DEFAULT_CONFIG["results_dir"]) / "runs.sqlite"
store = RunsStore(_db_path)
