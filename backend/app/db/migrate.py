import re
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_NAME = re.compile(r"^(\d+)_.+\.sql$")


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending numbered .sql files; returns the resulting schema version."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT max(version) FROM schema_version").fetchone()
    current = row[0] or 0
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = _NAME.match(path.name)
        if not match or int(match.group(1)) <= current:
            continue
        version = int(match.group(1))
        # executescript commits first; the version row lands with the script's changes.
        conn.executescript(
            f"BEGIN;\n{path.read_text()}\nINSERT INTO schema_version(version) VALUES ({version});\nCOMMIT;"
        )
        current = version
    return current
