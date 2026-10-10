import sqlite3
import struct

from app.db import _util

EMBEDDING_DIM = 1536
PROSE = "prose"


def create(conn: sqlite3.Connection, *, type: str, body: str, record_id: int | None = None,
           track_id: int | None = None) -> int:
    """Raises sqlite3.IntegrityError unless exactly one of record_id / track_id is set."""
    return _util.insert(
        conn, "notes",
        {"type": type, "body": body, "record_id": record_id, "track_id": track_id},
    )


def get(conn: sqlite3.Connection, note_id: int) -> dict | None:
    return _util.get(conn, "notes", note_id)


def list_for_record(conn: sqlite3.Connection, record_id: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM notes WHERE record_id = ? ORDER BY id", (record_id,))
    return [dict(r) for r in rows]


def list_for_track(conn: sqlite3.Connection, track_id: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM notes WHERE track_id = ? ORDER BY id", (track_id,))
    return [dict(r) for r in rows]


def update(conn: sqlite3.Connection, note_id: int, **values) -> None:
    _util.update(conn, "notes", note_id,
                 {**values, "updated_at": _now(conn)}, {"type", "body", "updated_at"})
    note = get(conn, note_id)
    if note and note["type"] != PROSE:
        delete_embedding(conn, note_id)


def delete(conn: sqlite3.Connection, note_id: int) -> bool:
    delete_embedding(conn, note_id)
    return _util.delete(conn, "notes", note_id)


def search(conn: sqlite3.Connection, query: str) -> list[dict]:
    rows = conn.execute(
        "SELECT n.* FROM notes_fts f JOIN notes n ON n.id = f.rowid "
        "WHERE notes_fts MATCH ? ORDER BY rank",
        (query,),
    )
    return [dict(r) for r in rows]


def _now(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT strftime('%Y-%m-%dT%H:%M:%SZ', 'now')").fetchone()[0]


def _blob(vector: list[float]) -> bytes:
    if len(vector) != EMBEDDING_DIM:
        raise ValueError(f"embedding must have {EMBEDDING_DIM} dimensions")
    return struct.pack(f"{EMBEDDING_DIM}f", *vector)


def set_embedding(conn: sqlite3.Connection, note_id: int, vector: list[float]) -> None:
    note = get(conn, note_id)
    if note is None or note["type"] != PROSE:
        raise ValueError("only existing notes of type 'prose' can have embeddings")
    blob = _blob(vector)
    conn.execute("DELETE FROM note_embeddings WHERE note_id = ?", (note_id,))
    conn.execute("INSERT INTO note_embeddings(note_id, embedding) VALUES (?, ?)", (note_id, blob))
    conn.commit()


def delete_embedding(conn: sqlite3.Connection, note_id: int) -> None:
    conn.execute("DELETE FROM note_embeddings WHERE note_id = ?", (note_id,))
    conn.commit()


def has_embedding(conn: sqlite3.Connection, note_id: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM note_embeddings WHERE note_id = ?", (note_id,)
    ).fetchone() is not None
