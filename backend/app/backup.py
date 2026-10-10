"""Copy the SQLite database to a timestamped file (safe while the app is running).

CLI: python -m app.backup
"""
import sqlite3
import time
from pathlib import Path

from app import config

BACKUP_DIR = config.BACKEND_DIR / "backups"
KEEP = 14  # newest copies kept by the nightly run


def backup(db_path: Path | None = None, dest_dir: Path | None = None, keep: int | None = None) -> Path:
    source = Path(db_path or config.DB_PATH)
    if not source.exists():
        raise FileNotFoundError(f"no database at {source}")
    dest_dir = Path(dest_dir or BACKUP_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{source.stem}-{time.strftime('%Y%m%d-%H%M%S')}{source.suffix}"
    src = sqlite3.connect(source)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)  # consistent snapshot even with writers active
    finally:
        dst.close()
        src.close()
    if keep:
        copies = sorted(dest_dir.glob(f"{source.stem}-*{source.suffix}"))
        for old in copies[:-keep]:
            old.unlink()
    return dest


def main() -> None:
    print(backup(keep=KEEP))


if __name__ == "__main__":
    main()
