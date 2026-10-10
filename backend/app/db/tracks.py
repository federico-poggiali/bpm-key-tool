import json
import sqlite3

from app.db import _util, notes

_COLUMNS = {"position", "artist", "title", "duration_sec", "bpm", "key", "camelot_key", "confidence",
            "analysis_raw", "audio_path", "analyzed_at", "bpm_manual", "key_manual"}


def _prepare(values: dict) -> dict:
    raw = values.get("analysis_raw")
    if raw is not None and not isinstance(raw, str):
        values = {**values, "analysis_raw": json.dumps(raw)}
    return values


def _out(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    track = dict(row)
    if track["analysis_raw"] is not None:
        track["analysis_raw"] = json.loads(track["analysis_raw"])
    return track


def create(conn: sqlite3.Connection, record_id: int, **values) -> int:
    return _util.insert(conn, "tracks", _prepare({"record_id": record_id, **values}))


def get(conn: sqlite3.Connection, track_id: int) -> dict | None:
    return _out(conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone())


def list_for_record(conn: sqlite3.Connection, record_id: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM tracks WHERE record_id = ? ORDER BY id", (record_id,))
    return [_out(r) for r in rows]


def update(conn: sqlite3.Connection, track_id: int, **values) -> None:
    _util.update(conn, "tracks", track_id, _prepare(values), _COLUMNS)


def delete(conn: sqlite3.Connection, track_id: int) -> bool:
    notes.delete_embeddings_for_track(conn, track_id)
    return _util.delete(conn, "tracks", track_id)
