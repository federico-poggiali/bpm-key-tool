"""The real app on one port for browser tests: throwaway DB, vault and audio folders; Discogs and the
BPM lookup are faked (saved real responses, deterministic tempo/key). Never touches real data.

    E2E_DIR=/some/empty/dir PORT=8100 python backend/tests/e2e_server.py
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(os.environ.get("E2E_DIR", ROOT / "frontend" / "e2e" / ".run")).resolve()
shutil.rmtree(RUN, ignore_errors=True)
for name in ("audio", "vault"):
    (RUN / name).mkdir(parents=True)
os.environ.update(DB_PATH=str(RUN / "e2e.db"), AUDIO_DIR=str(RUN / "audio"), VAULT_DIR=str(RUN / "vault"),
                  DISCOGS_TOKEN="e2e-fake-token")
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

import httpx  # noqa: E402
import uvicorn  # noqa: E402

import app.main as main  # noqa: E402
from app.analysis import job as analysis_job  # noqa: E402
from app.deps import get_discogs  # noqa: E402
from app.discogs import DiscogsClient  # noqa: E402
from app.vault import VaultSyncer  # noqa: E402
from tests.conftest import fake_discogs_transport  # noqa: E402

owned: dict[int, list[int]] = {}


def discogs() -> DiscogsClient:
    return DiscogsClient("e2e", client=httpx.Client(transport=fake_discogs_transport(collection=owned)),
                         sleep=lambda s: None)


def fake_lookup(record, tracks, release):
    keys = [("8A", "A minor"), ("4A", "F minor"), ("9B", "G major"), ("11A", "F# minor")]
    return {t["id"]: {"bpm": 120.0 + 4 * i, "key": keys[i % 4][1], "camelot_key": keys[i % 4][0],
                      "confidence": 0.7 if i % 3 else 0.2,
                      "raw": {"status": "analyzed", "bpm_alt": 60.0 + 2 * i, "measurements": []}}
            for i, t in enumerate(tracks)}


_make_handler = analysis_job.make_handler
analysis_job.make_handler = lambda factory, **kw: _make_handler(factory, lookup_fn=fake_lookup, **kw)
main._discogs = discogs
main.app.dependency_overrides[get_discogs] = discogs
_original_init = VaultSyncer.__init__
VaultSyncer.__init__ = lambda self, vault_dir=None, delay=0.3: _original_init(self, vault_dir, delay)

if __name__ == "__main__":
    uvicorn.run(main.app, host="127.0.0.1", port=int(os.environ.get("PORT", "8100")), log_level="warning")
