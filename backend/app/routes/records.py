import sqlite3
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from app import intake as intake_service
from app import sync
from app.analysis import job as analysis_job
from app.analysis.camelot import to_camelot
from app.db import proposals, queries, records, tracks
from app.deps import get_db, get_discogs, get_discogs_lazy, get_runner
from app.discogs import DiscogsClient, DiscogsError, DiscogsNotFound, release_to_record
from app.jobs.runner import JobRunner
from app.schemas import (
    AudioMatchReport,
    DiscardRequest,
    IntakeResponse,
    JobStarted,
    Page,
    RecordDetail,
    RecordPatch,
    RecordSummary,
    Status,
    ValidateRequest,
)

router = APIRouter(prefix="/api/records", tags=["records"])


class AnalyzeRequest(BaseModel):
    track_ids: list[int] | None = None  # omitted: the whole record


class IntakeRequest(BaseModel):
    discogs_url: str
    status: Status = "owned"


def require_record(conn: sqlite3.Connection, record_id: int) -> dict:
    record = records.get(conn, record_id)
    if record is None:
        raise HTTPException(404, "record not found")
    return record


def filters_from_query(bpm_min, bpm_max, key, tag, style, status, q, limit, offset) -> queries.Filters:
    camelot = None
    if key:
        camelot = to_camelot(key)
        if camelot is None:
            raise HTTPException(422, f"unrecognised key '{key}' (use e.g. 'F# minor', 'Am' or '11A')")
    return queries.Filters(bpm_min=bpm_min, bpm_max=bpm_max, camelot=camelot,
                           tags=[t.strip().lower() for t in tag if t.strip()],
                           styles=records.clean_styles(style), status=status,
                           q=q, limit=limit, offset=offset)


@router.post("/intake", response_model=IntakeResponse)
def intake(body: IntakeRequest, response: Response, conn: sqlite3.Connection = Depends(get_db),
           discogs: DiscogsClient = Depends(get_discogs)) -> dict:
    try:
        result = intake_service.intake(conn, discogs, body.discogs_url, body.status)
    except DiscogsNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except DiscogsError as exc:
        raise HTTPException(400 if "Not a Discogs" in str(exc) else 502, str(exc)) from exc
    response.status_code = 201 if result.created else 200
    body_out = {**result.record, "resolved_from_master": result.resolved_from_master, "jobs": None}
    return body_out


@router.get("", response_model=Page[RecordSummary])
def list_records(
    conn: sqlite3.Connection = Depends(get_db),
    bpm_min: Annotated[float | None, Query(ge=0)] = None,
    bpm_max: Annotated[float | None, Query(ge=0)] = None,
    key: str | None = None,
    tag: Annotated[list[str], Query()] = [],  # noqa: B006 (FastAPI query default)
    style: Annotated[list[str], Query()] = [],  # noqa: B006
    status: Status | None = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    f = filters_from_query(bpm_min, bpm_max, key, tag, style, status, q, limit, offset)
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
                 runner: JobRunner = Depends(get_runner),
                 discogs: Callable[[], DiscogsClient] = Depends(get_discogs_lazy)) -> dict:
    before = require_record(conn, record_id)
    changes = body.model_dump(exclude_unset=True)
    if any(changes.get(k, "x") is None for k in ("artist", "title", "status", "styles")):
        raise HTTPException(422, "artist, title, status and styles cannot be null")
    if changes.pop("reset_styles", False):
        if "styles" in changes:
            raise HTTPException(422, "send either styles or reset_styles, not both")
        changes.update(_discogs_styles(before, discogs))
    elif "styles" in changes:
        changes["styles_manual"] = 1  # what the user types always wins over Discogs
    records.update(conn, record_id, **changes)
    # Moving a record to 'owned' adds it to Discogs, as intake would. Moving away never removes it.
    if (changes.get("status") == "owned" and before["status"] != "owned"
            and not before["discogs_collection_synced"] and before["discogs_release_id"]):
        runner.enqueue(sync.JOB_TYPE, record_id)
    return queries.record_detail(conn, record_id)


def _discogs_styles(record: dict, discogs: Callable[[], DiscogsClient]) -> dict:
    """Fetch the record's styles (and catno) afresh and release the manual lock."""
    if record["discogs_release_id"] is None:
        raise HTTPException(400, "record has no Discogs release id, so nothing to re-fetch")
    try:
        fresh = release_to_record(discogs().release(record["discogs_release_id"]))
    except DiscogsNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except DiscogsError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"styles": fresh["styles"], "styles_manual": 0}


@router.delete("/{record_id}", status_code=204)
def delete_record(record_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    require_record(conn, record_id)
    records.delete(conn, record_id)  # also removes tracks, notes, tags links; Discogs is untouched
    return Response(status_code=204)


@router.get("/{record_id}/audio-match", response_model=AudioMatchReport)
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
def analyze(record_id: int, body: AnalyzeRequest | None = None, conn: sqlite3.Connection = Depends(get_db),
            runner: JobRunner = Depends(get_runner)) -> dict:
    """Analyse the whole record, or only `track_ids` when given."""
    record = require_record(conn, record_id)
    params = None
    if body and body.track_ids is not None:
        own = {t["id"] for t in tracks.list_for_record(conn, record_id)}
        if not body.track_ids or not set(body.track_ids) <= own:
            raise HTTPException(400, "track_ids must be a non-empty list of tracks on this record")
        params = {"track_ids": sorted(set(body.track_ids))}
    if record["discogs_release_id"] is None:
        raise HTTPException(400, "record has no Discogs release id, so nothing to look up")
    return {"job_id": runner.enqueue(analysis_job.JOB_TYPE, record_id, params), "status": "queued"}


NOT_PENDING = "track_ids must be tracks of this record with analysis waiting for validation"


@router.post("/{record_id}/validate", response_model=RecordDetail)
def validate(record_id: int, body: ValidateRequest, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Save the chosen tracks' analysis proposals onto them. Only records you own can be validated."""
    record = require_record(conn, record_id)
    if record["status"] != "owned":
        raise HTTPException(409, "only records in your library can be validated; this one is not owned")
    pending = proposals.for_record(conn, record_id)
    if not set(body.track_ids) <= set(pending):
        raise HTTPException(400, NOT_PENDING)
    analysis_job.validate(conn, sorted(set(body.track_ids)), body.overwrite_manual)
    return queries.record_detail(conn, record_id)


@router.post("/{record_id}/discard", response_model=RecordDetail)
def discard(record_id: int, body: DiscardRequest | None = None,
            conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Drop analysis proposals (all of them, or only `track_ids`) without touching the tracks."""
    require_record(conn, record_id)
    pending = proposals.for_record(conn, record_id)
    ids = list(pending) if body is None or body.track_ids is None else body.track_ids
    if not set(ids) <= set(pending):
        raise HTTPException(400, NOT_PENDING)
    proposals.delete(conn, ids)
    return queries.record_detail(conn, record_id)
