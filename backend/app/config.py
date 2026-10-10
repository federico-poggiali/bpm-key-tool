import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


def _load_dotenv() -> None:
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _path(name: str, default: Path) -> Path:
    """Env paths may be relative; they resolve against the repo root."""
    value = os.environ.get(name)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


_load_dotenv()

DB_PATH = _path("DB_PATH", BACKEND_DIR / "data" / "vinyl.db")
AUDIO_DIR = _path("AUDIO_DIR", REPO_ROOT / "audio")
VAULT_DIR = _path("VAULT_DIR", REPO_ROOT / "vault")
DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN", "")
USER_AGENT = f"VinylSecondBrain/0.1 ( {os.environ.get('CONTACT_EMAIL', '')} )"
CORS_ORIGINS = [o.strip() for o in os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
