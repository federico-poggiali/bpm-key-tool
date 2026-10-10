from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import config
from app.vault import VaultSyncer

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
