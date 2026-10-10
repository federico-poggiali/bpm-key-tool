import subprocess
import sys

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import config
from app.schemas import OpenedPath
from app.vault import EXAMPLES_FILE, VaultSyncer

router = APIRouter(prefix="/api/admin", tags=["admin"])


class VaultSyncOut(BaseModel):
    written: int
    skipped: int
    deleted: int
    synced_at: str


class VaultStatus(BaseModel):
    vault_dir: str
    last_sync: VaultSyncOut | None
    last_error: str | None


def _syncer(request: Request) -> VaultSyncer:
    syncer = getattr(request.app.state, "vault_syncer", None)
    if syncer is None:
        raise HTTPException(503, "vault sync is not running")
    return syncer


@router.post("/sync-vault", response_model=VaultSyncOut)
def sync_vault_now(request: Request) -> dict:
    return _syncer(request).run_now()


@router.get("/vault-status", response_model=VaultStatus)
def vault_status(request: Request) -> dict:
    syncer = _syncer(request)
    return {"vault_dir": str(syncer.vault_dir or config.VAULT_DIR), "last_sync": syncer.last_result,
            "last_error": syncer.last_error}


@router.post("/open-vault", response_model=OpenedPath)
def open_vault() -> dict:
    """Reveal the Dataview examples file in Finder (macOS only; elsewhere just report the path)."""
    target = config.VAULT_DIR / EXAMPLES_FILE
    if sys.platform != "darwin" or not target.exists():
        return {"opened": False, "path": str(target)}
    subprocess.run(["open", "-R", str(target)], check=False)
    return {"opened": True, "path": str(target)}
