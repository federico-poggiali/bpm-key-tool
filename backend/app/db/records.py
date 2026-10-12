import json
import sqlite3

from app.db import _util, notes

_COLUMNS = {"discogs_release_id", "artist", "title", "label", "year", "format", "cover_url",
            "status", "discogs_collection_synced", "styles", "styles_manual", "catno"}


def clean_styles(styles: list[str]) -> list[str]:
    """Trim, drop empties and de-duplicate case-insensitively, keeping the first spelling."""
    seen: set[str] = set()
    out = []
    for style in styles:
        style = " ".join(style.split())
        if style and style.lower() not in seen:
            seen.add(style.lower())
            out.append(style)
    return out


def _encode(values: dict) -> dict:
    if values.get("styles") is not None:
        values = {**values, "styles": json.dumps(clean_styles(values["styles"]), ensure_ascii=False)}
    return values


def decode(row: dict | None) -> dict | None:
    """styles comes back as a list, or None when it was never fetched."""
    if row is not None and row.get("styles") is not None:
        row["styles"] = json.loads(row["styles"])
    return row


def create(conn: sqlite3.Connection, **values) -> int:
    return _util.insert(conn, "records", _encode(values))


def get(conn: sqlite3.Connection, record_id: int) -> dict | None:
    return decode(_util.get(conn, "records", record_id))


def get_by_discogs_id(conn: sqlite3.Connection, release_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM records WHERE discogs_release_id = ?", (release_id,)
    ).fetchone()
    return decode(dict(row)) if row else None


def list_all(conn: sqlite3.Connection) -> list[dict]:
    return [decode(dict(r)) for r in conn.execute("SELECT * FROM records ORDER BY id")]


def update(conn: sqlite3.Connection, record_id: int, **values) -> None:
    _util.update(conn, "records", record_id, _encode(values), _COLUMNS)


def delete(conn: sqlite3.Connection, record_id: int) -> bool:
    notes.delete_embeddings_for_record(conn, record_id)
    return _util.delete(conn, "records", record_id)


def search(conn: sqlite3.Connection, query: str) -> list[dict]:
    rows = conn.execute(
        "SELECT r.* FROM records_fts f JOIN records r ON r.id = f.rowid "
        "WHERE records_fts MATCH ? ORDER BY rank",
        (query,),
    )
    return [decode(dict(r)) for r in rows]
