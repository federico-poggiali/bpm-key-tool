import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app import intake as intake_service
from app import sync
from app.analysis import job as analysis_job
from app.db import records
from app.deps import get_db, get_discogs, get_runner
from app.discogs import DiscogsClient, DiscogsError, DiscogsNotFound
from app.jobs.runner import JobRunner

router = APIRouter(prefix="/api/records", tags=["records"])


class IntakeRequest(BaseModel):
    discogs_url: str
    status: Literal["owned", "wantlist", "considering"] = "owned"


def _require_record(conn: sqlite3.Connection, record_id: int) -> dict:
    record = records.get(conn, record_id)
    if record is None:
        raise HTTPException(404, "record not found")
    return record


@router.post("/intake")
def intake(body: IntakeRequest, response: Response, conn: sqlite3.Connection = Depends(get_db),
           discogs: DiscogsClient = Depends(get_discogs),
           runner: JobRunner = Depends(get_runner)) -> dict:
    try:
        result = intake_service.intake(conn, discogs, body.discogs_url, body.status)
    except DiscogsNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except DiscogsError as exc:
        raise HTTPException(400 if "Not a Discogs" in str(exc) else 502, str(exc)) from exc
    response.status_code = 201 if result.created else 200
    body_out = {**result.record, "resolved_from_master": result.resolved_from_master, "jobs": None}
    if result.created:
        # Independent jobs: one failing never blocks the other.
        record_id = result.record["id"]
        body_out["jobs"] = {
            "analysis": runner.enqueue(analysis_job.JOB_TYPE, record_id),
            "discogs_sync": runner.enqueue(sync.JOB_TYPE, record_id) if result.record["status"] == "owned"
            else None,
        }
    return body_out


@router.get("/{record_id}/audio-match")
def audio_match(record_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    _require_record(conn, record_id)
    return analysis_job.match_report(conn, record_id)


@router.post("/{record_id}/sync-discogs", status_code=202)
def sync_discogs(record_id: int, conn: sqlite3.Connection = Depends(get_db),
                 runner: JobRunner = Depends(get_runner)) -> dict:
    record = _require_record(conn, record_id)
    if record["status"] != "owned":
        raise HTTPException(400, f"only owned records are collected (status: {record['status']})")
    return {"job_id": runner.enqueue(sync.JOB_TYPE, record_id), "status": "queued"}


@router.post("/{record_id}/analyze", status_code=202)
def analyze(record_id: int, conn: sqlite3.Connection = Depends(get_db),
            runner: JobRunner = Depends(get_runner)) -> dict:
    record = _require_record(conn, record_id)
    if record["discogs_release_id"] is None:
        raise HTTPException(400, "record has no Discogs release id, so no audio folder")
    job_id = runner.enqueue(analysis_job.JOB_TYPE, record_id)
    return {"job_id": job_id, "status": "queued"}
