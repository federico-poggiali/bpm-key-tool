import sqlite3
from typing import Any


def insert(conn: sqlite3.Connection, table: str, values: dict[str, Any]) -> int:
    cols = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(values.values()))
    conn.commit()
    return cur.lastrowid


def update(conn: sqlite3.Connection, table: str, row_id: int, values: dict[str, Any],
           allowed: set[str]) -> None:
    bad = set(values) - allowed
    if bad:
        raise ValueError(f"cannot update columns: {sorted(bad)}")
    if not values:
        return
    sets = ", ".join(f"{c} = ?" for c in values)
    conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?", [*values.values(), row_id])
    conn.commit()


def get(conn: sqlite3.Connection, table: str, row_id: int) -> dict | None:
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    return dict(row) if row else None


def delete(conn: sqlite3.Connection, table: str, row_id: int) -> bool:
    cur = conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
    conn.commit()
    return cur.rowcount > 0
