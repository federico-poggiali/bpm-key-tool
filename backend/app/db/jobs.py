import json
import sqlite3

from app.db import _util


def _out(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    job = dict(row)
    if job["result"] is not None:
        job["result"] = json.loads(job["result"])
    job["params"] = json.loads(job["params"]) if job.get("params") else None
    return job


def create(conn: sqlite3.Connection, type: str, record_id: int | None = None,
           params: dict | None = None) -> int:
    values = {"type": type, "record_id": record_id}
    if params is not None:
        values["params"] = json.dumps(params)
    return _util.insert(conn, "jobs", values)


def get(conn: sqlite3.Connection, job_id: int) -> dict | None:
    return _out(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())


def list_by_status(conn: sqlite3.Connection, status: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY id", (status,))
    return [_out(r) for r in rows]


def set_status(conn: sqlite3.Connection, job_id: int, status: str, *, error: str | None = None,
               result: dict | None = None) -> None:
    conn.execute(
        "UPDATE jobs SET status = ?, error = ?, result = ?, "
        "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
        (status, error, json.dumps(result) if result is not None else None, job_id),
    )
    conn.commit()
