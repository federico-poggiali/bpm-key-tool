import sqlite3


def _link_table(kind: str) -> tuple[str, str]:
    if kind not in ("record", "track"):
        raise ValueError("kind must be 'record' or 'track'")
    return f"{kind}_tags", f"{kind}_id"


def get_or_create(conn: sqlite3.Connection, name: str) -> int:
    name = name.strip().lower()
    if not name:
        raise ValueError("tag name is empty")
    conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (name,))
    conn.commit()
    return conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()[0]


def add(conn: sqlite3.Connection, kind: str, item_id: int, name: str) -> None:
    table, col = _link_table(kind)
    tag_id = get_or_create(conn, name)
    conn.execute(f"INSERT OR IGNORE INTO {table}({col}, tag_id) VALUES (?, ?)", (item_id, tag_id))
    conn.commit()


def remove(conn: sqlite3.Connection, kind: str, item_id: int, name: str) -> bool:
    table, col = _link_table(kind)
    cur = conn.execute(
        f"DELETE FROM {table} WHERE {col} = ? AND tag_id = (SELECT id FROM tags WHERE name = ?)",
        (item_id, name.strip().lower()),
    )
    conn.commit()
    return cur.rowcount > 0


def for_item(conn: sqlite3.Connection, kind: str, item_id: int) -> list[str]:
    table, col = _link_table(kind)
    rows = conn.execute(
        f"SELECT t.name FROM {table} l JOIN tags t ON t.id = l.tag_id "
        f"WHERE l.{col} = ? ORDER BY t.name",
        (item_id,),
    )
    return [r[0] for r in rows]


def list_with_counts(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT t.name, "
        "(SELECT count(*) FROM record_tags WHERE tag_id = t.id) AS record_count, "
        "(SELECT count(*) FROM track_tags WHERE tag_id = t.id) AS track_count "
        "FROM tags t ORDER BY t.name"
    )
    return [dict(r) for r in rows]
