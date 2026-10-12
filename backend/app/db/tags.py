import sqlite3


def _link_table(kind: str) -> tuple[str, str]:
    if kind not in ("record", "track"):
        raise ValueError("kind must be 'record' or 'track'")
    return f"{kind}_tags", f"{kind}_id"


def _clean(name: str) -> str:
    name = name.strip().lower()
    if not name:
        raise ValueError("tag name is empty")
    return name


# ---- groups and tag definitions (the Tag Manager) ----

def list_groups(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT id, name, fixed FROM tag_groups ORDER BY position, id")
    groups = [dict(r) | {"tags": []} for r in rows]
    by_id = {g["id"]: g for g in groups}
    rows = conn.execute(
        "SELECT t.id, t.name, t.group_id, "
        "(SELECT count(*) FROM record_tags WHERE tag_id = t.id) AS record_count, "
        "(SELECT count(*) FROM track_tags WHERE tag_id = t.id) AS track_count "
        "FROM tags t WHERE t.group_id IS NOT NULL ORDER BY t.name"
    )
    for r in rows:
        by_id[r["group_id"]]["tags"].append({k: r[k] for k in ("id", "name", "record_count", "track_count")})
    for g in groups:
        g["fixed"] = bool(g["fixed"])
    return groups


def create_group(conn: sqlite3.Connection, name: str) -> int:
    name = name.strip()
    if not name:
        raise ValueError("group name is empty")
    try:
        cur = conn.execute(
            "INSERT INTO tag_groups(name, position) "
            "VALUES (?, (SELECT coalesce(max(position), -1) + 1 FROM tag_groups))", (name,))
    except sqlite3.IntegrityError as e:
        raise ValueError(f"a group called '{name}' already exists") from e
    conn.commit()
    return cur.lastrowid


def _group(conn: sqlite3.Connection, group_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT id, fixed FROM tag_groups WHERE id = ?", (group_id,)).fetchone()
    if row is None:
        raise LookupError("group not found")
    return row


def rename_group(conn: sqlite3.Connection, group_id: int, name: str) -> None:
    if _group(conn, group_id)["fixed"]:
        raise PermissionError("the energy, atmosphere and set role groups cannot be renamed")
    name = name.strip()
    if not name:
        raise ValueError("group name is empty")
    try:
        conn.execute("UPDATE tag_groups SET name = ? WHERE id = ?", (name, group_id))
    except sqlite3.IntegrityError as e:
        raise ValueError(f"a group called '{name}' already exists") from e
    conn.commit()


def delete_group(conn: sqlite3.Connection, group_id: int) -> None:
    if _group(conn, group_id)["fixed"]:
        raise PermissionError("the energy, atmosphere and set role groups cannot be deleted")
    conn.execute("DELETE FROM tag_groups WHERE id = ?", (group_id,))  # its tags and their links go too
    conn.commit()


def create_tag(conn: sqlite3.Connection, group_id: int, name: str) -> int:
    _group(conn, group_id)
    name = _clean(name)
    try:
        cur = conn.execute("INSERT INTO tags(name, group_id) VALUES (?, ?)", (name, group_id))
    except sqlite3.IntegrityError as e:
        raise ValueError(f"the tag '{name}' already exists") from e
    conn.commit()
    return cur.lastrowid


def update_tag(conn: sqlite3.Connection, tag_id: int, name: str | None = None,
               group_id: int | None = None) -> None:
    if conn.execute("SELECT 1 FROM tags WHERE id = ?", (tag_id,)).fetchone() is None:
        raise LookupError("tag not found")
    try:
        if name is not None:
            conn.execute("UPDATE tags SET name = ? WHERE id = ?", (_clean(name), tag_id))
        if group_id is not None:
            _group(conn, group_id)
            conn.execute("UPDATE tags SET group_id = ? WHERE id = ?", (group_id, tag_id))
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError("another tag already has that name") from e
    conn.commit()


def delete_tag(conn: sqlite3.Connection, tag_id: int) -> None:
    if conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,)).rowcount == 0:
        raise LookupError("tag not found")
    conn.commit()


# ---- putting defined tags on records and tracks ----

def add(conn: sqlite3.Connection, kind: str, item_id: int, name: str) -> None:
    """Put a tag defined in the Tag Manager on a record or track; an undefined name is refused."""
    table, col = _link_table(kind)
    row = conn.execute("SELECT id FROM tags WHERE name = ? AND group_id IS NOT NULL",
                       (_clean(name),)).fetchone()
    if row is None:
        raise LookupError(f"no tag called '{name.strip()}': design it in the Tag Manager first")
    conn.execute(f"INSERT OR IGNORE INTO {table}({col}, tag_id) VALUES (?, ?)", (item_id, row[0]))
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
        "SELECT t.name, g.name AS \"group\", "
        "(SELECT count(*) FROM record_tags WHERE tag_id = t.id) AS record_count, "
        "(SELECT count(*) FROM track_tags WHERE tag_id = t.id) AS track_count "
        "FROM tags t JOIN tag_groups g ON g.id = t.group_id ORDER BY g.position, t.name"
    )
    return [dict(r) for r in rows]
