import sqlite3

from app.db import _util

_COLUMNS = {"discogs_release_id", "artist", "title", "label", "year", "format", "cover_url",
            "status", "discogs_collection_synced"}


def create(conn: sqlite3.Connection, **values) -> int:
    return _util.insert(conn, "records", values)


def get(conn: sqlite3.Connection, record_id: int) -> dict | None:
    return _util.get(conn, "records", record_id)


def get_by_discogs_id(conn: sqlite3.Connection, release_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM records WHERE discogs_release_id = ?", (release_id,)
    ).fetchone()
    return dict(row) if row else None


def list_all(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM records ORDER BY id")]


def update(conn: sqlite3.Connection, record_id: int, **values) -> None:
    _util.update(conn, "records", record_id, values, _COLUMNS)


def delete(conn: sqlite3.Connection, record_id: int) -> bool:
    return _util.delete(conn, "records", record_id)


def search(conn: sqlite3.Connection, query: str) -> list[dict]:
    rows = conn.execute(
        "SELECT r.* FROM records_fts f JOIN records r ON r.id = f.rowid "
        "WHERE records_fts MATCH ? ORDER BY rank",
        (query,),
    )
    return [dict(r) for r in rows]
