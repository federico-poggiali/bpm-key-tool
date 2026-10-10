import sqlite3
from pathlib import Path

import sqlite_vec

from app import config


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open a connection with foreign keys on and sqlite-vec loaded."""
    target = str(path if path is not None else config.DB_PATH)
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    # The API writes while the job worker does; FastAPI may open and close a request's connection on
    # different worker threads, which is safe because a connection is never shared between requests.
    conn = sqlite3.connect(target, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA foreign_keys = ON")
    if target != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    return conn
