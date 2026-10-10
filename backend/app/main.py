import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from app import config, errors, sync
from app.analysis import job as analysis_job
from app.db import connect, migrate
from app.discogs import DiscogsClient
from app.jobs.runner import JobRunner
from app.logging_config import configure as configure_logging
from app.routes import admin, jobs, notes, records, search, tags, tracks
from app.vault import VaultSyncer

log = logging.getLogger("app.request")


def _discogs() -> DiscogsClient:
    return DiscogsClient(config.DISCOGS_TOKEN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    conn = connect()
    migrate(conn)
    conn.close()
    syncer = app.state.vault_syncer = VaultSyncer(config.VAULT_DIR)
    app.state.runner = JobRunner({
        analysis_job.JOB_TYPE: analysis_job.make_handler(_discogs),
        sync.JOB_TYPE: sync.make_handler(_discogs),
    }, on_done=syncer.request)
    app.state.runner.start()
    syncer.request()  # bring the vault up to date at startup
    yield
    app.state.runner.stop()
    syncer.stop()


def _operation_id(route: APIRoute) -> str:
    return route.name  # readable names for the generated TypeScript client


app = FastAPI(title="Vinyl Second-Brain", lifespan=lifespan, generate_unique_id_function=_operation_id)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"],
                   allow_headers=["*"])
errors.install(app)
for module in (records, tracks, notes, tags, search, jobs, admin):
    app.include_router(module.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    log.info("request", extra={"method": request.method, "path": request.url.path,
                               "status": response.status_code,
                               "ms": round((time.perf_counter() - start) * 1000, 1)})
    return response


@app.middleware("http")
async def refresh_vault_after_writes(request: Request, call_next):
    response = await call_next(request)
    syncer = getattr(request.app.state, "vault_syncer", None)
    if (syncer and request.method in ("POST", "PATCH", "PUT", "DELETE")
            and response.status_code < 400 and not request.url.path.endswith("/sync-vault")):
        syncer.request()
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def mount_frontend(application: FastAPI, dist) -> bool:
    """Serve the built single-page app (and its client-side routes) from the same port as the API."""
    index = dist / "index.html"
    if not index.exists():
        return False
    if (dist / "assets").is_dir():
        application.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @application.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "not found")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)

    return True


mount_frontend(app, config.FRONTEND_DIST)
