import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN", "")
GETSONGBPM_KEY = os.environ.get("GETSONGBPM_KEY", "")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")
USER_AGENT = f"BpmKeyTool/0.1 ( {CONTACT_EMAIL} )"
CACHE_PATH = ROOT / "cache.sqlite"
