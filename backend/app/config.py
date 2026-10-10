import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

DB_PATH = Path(os.environ.get("DB_PATH", BACKEND_DIR / "data" / "vinyl.db"))
