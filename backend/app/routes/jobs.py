import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import jobs
from app.deps import get_db
from app.schemas import JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    job = jobs.get(conn, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job
