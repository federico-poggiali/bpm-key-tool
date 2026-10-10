from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.analysis import job as analysis_job
from app.db import connect, migrate
from app.jobs.runner import JobRunner
from app.routes import jobs, records


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    migrate(conn)
    conn.close()
    app.state.runner = JobRunner({analysis_job.JOB_TYPE: analysis_job.make_handler()})
    app.state.runner.start()
    yield
    app.state.runner.stop()


app = FastAPI(title="Vinyl Second-Brain", lifespan=lifespan)
app.include_router(records.router)
app.include_router(jobs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
