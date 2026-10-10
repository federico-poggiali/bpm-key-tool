import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from app import intake as intake_service
from app import sync
from app.analysis import job as analysis_job
from app.analysis.camelot import to_camelot
from app.db import queries, records
from app.deps import get_db, get_discogs, get_runner
from app.discogs import DiscogsClient, DiscogsError, DiscogsNotFound
from app.jobs.runner import JobRunner
from app.schemas import IntakeResponse, JobStarted, Page, RecordDetail, RecordPatch, RecordSummary, Status

router = APIRouter(prefix="/api/records", tags=["records"])


class IntakeRequest(BaseModel):
    discogs_url: str
    status: Status = "owned"


def require_record(conn: sqlite3.Connection, record_id: int) -> dict:
    record = records.get(conn, record_id)
    if record is None:
        raise HTTPException(404, "record not found")
    return record


def filters_from_query(bpm_min, bpm_max, key, tag, status, q, limit, offset) -> queries.Filters:
    camelot = None
    if key:
        camelot = to_camelot(key)
        if camelot is None:
            raise HTTPException(422, f"unrecognised key '{key}' (use e.g. 'F# minor', 'Am' or '11A')")
    return queries.Filters(bpm_min=bpm_min, bpm_max=bpm_max, camelot=camelot,
                           tags=[t.strip().lower() for t in tag if t.strip()], status=status,
                           q=q, limit=limit, offset=offset)


@router.post("/intake", response_model=IntakeResponse)
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
            "discogs_sync": runner.enqueue(sync.JOB_TYPE, record_id)
            if result.record["status"] == "owned" else None,
        }
    return body_out


@router.get("", response_model=Page[RecordSummary])
def list_records(
    conn: sqlite3.Connection = Depends(get_db),
    bpm_min: Annotated[float | None, Query(ge=0)] = None,
    bpm_max: Annotated[float | None, Query(ge=0)] = None,
    key: str | None = None,
    tag: Annotated[list[str], Query()] = [],  # noqa: B006 (FastAPI query default)
    status: Status | None = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    f = filters_from_query(bpm_min, bpm_max, key, tag, status, q, limit, offset)
    items, total = queries.list_records(conn, f)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{record_id}", response_model=RecordDetail)
def get_record(record_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    detail = queries.record_detail(conn, record_id)
    if detail is None:
        raise HTTPException(404, "record not found")
    return detail


@router.patch("/{record_id}", response_model=RecordDetail)
def patch_record(record_id: int, body: RecordPatch, conn: sqlite3.Connection = Depends(get_db),
                 runner: JobRunner = Depends(get_runner)) -> dict:
    before = require_record(conn, record_id)
    changes = body.model_dump(exclude_unset=True)
    if any(changes.get(k, "x") is None for k in ("artist", "title", "status")):
        raise HTTPException(422, "artist, title and status cannot be null")
    records.update(conn, record_id, **changes)
    # Moving a record to 'owned' adds it to Discogs, as intake would. Moving away never removes it.
    if (changes.get("status") == "owned" and before["status"] != "owned"
            and not before["discogs_collection_synced"] and before["discogs_release_id"]):
        runner.enqueue(sync.JOB_TYPE, record_id)
    return queries.record_detail(conn, record_id)


@router.delete("/{record_id}", status_code=204)
def delete_record(record_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    require_record(conn, record_id)
    records.delete(conn, record_id)  # also removes tracks, notes, tags links; Discogs is untouched
    return Response(status_code=204)


@router.get("/{record_id}/audio-match")
def audio_match(record_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    require_record(conn, record_id)
    return analysis_job.match_report(conn, record_id)


@router.post("/{record_id}/sync-discogs", status_code=202, response_model=JobStarted)
def sync_discogs(record_id: int, conn: sqlite3.Connection = Depends(get_db),
                 runner: JobRunner = Depends(get_runner)) -> dict:
    record = require_record(conn, record_id)
    if record["status"] != "owned":
        raise HTTPException(400, f"only owned records are collected (status: {record['status']})")
    return {"job_id": runner.enqueue(sync.JOB_TYPE, record_id), "status": "queued"}


@router.post("/{record_id}/analyze", status_code=202, response_model=JobStarted)
def analyze(record_id: int, conn: sqlite3.Connection = Depends(get_db),
            runner: JobRunner = Depends(get_runner)) -> dict:
    record = require_record(conn, record_id)
    if record["discogs_release_id"] is None:
        raise HTTPException(400, "record has no Discogs release id, so nothing to look up")
    return {"job_id": runner.enqueue(analysis_job.JOB_TYPE, record_id), "status": "queued"}
