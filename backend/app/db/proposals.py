"""Analysis results waiting for the owner to validate them (one per track; a new run replaces it)."""
import json
import sqlite3


def _out(row: sqlite3.Row) -> dict:
    p = dict(row)
    if p["analysis_raw"] is not None:
        p["analysis_raw"] = json.loads(p["analysis_raw"])
    return p


def put(conn: sqlite3.Connection, track_id: int, *, bpm, key, camelot_key, confidence, analysis_raw,
        audio_path, proposed_at: str) -> None:
    raw = analysis_raw
    if raw is not None and not isinstance(raw, str):
        raw = json.dumps(raw)
    conn.execute(
        "INSERT OR REPLACE INTO track_proposals (track_id, bpm, key, camelot_key, confidence, analysis_raw,"
        " audio_path, proposed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (track_id, bpm, key, camelot_key, confidence, raw, audio_path, proposed_at))
    conn.commit()


def get(conn: sqlite3.Connection, track_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM track_proposals WHERE track_id = ?", (track_id,)).fetchone()
    return _out(row) if row else None


def for_record(conn: sqlite3.Connection, record_id: int) -> dict[int, dict]:
    rows = conn.execute("SELECT p.* FROM track_proposals p JOIN tracks t ON t.id = p.track_id"
                        " WHERE t.record_id = ?", (record_id,))
    return {r["track_id"]: _out(r) for r in rows}


def delete(conn: sqlite3.Connection, track_ids: list[int]) -> None:
    conn.executemany("DELETE FROM track_proposals WHERE track_id = ?", [(i,) for i in track_ids])
    conn.commit()
