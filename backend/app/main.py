from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config, sync
from app.analysis import job as analysis_job
from app.db import connect, migrate
from app.discogs import DiscogsClient
from app.jobs.runner import JobRunner
from app.routes import jobs, records


def _discogs() -> DiscogsClient:
    return DiscogsClient(config.DISCOGS_TOKEN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    migrate(conn)
    conn.close()
    app.state.runner = JobRunner({
        analysis_job.JOB_TYPE: analysis_job.make_handler(_discogs),
        sync.JOB_TYPE: sync.make_handler(_discogs),
    })
    app.state.runner.start()
    yield
    app.state.runner.stop()


app = FastAPI(title="Vinyl Second-Brain", lifespan=lifespan)
app.include_router(records.router)
app.include_router(jobs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
