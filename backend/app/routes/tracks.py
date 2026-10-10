import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analysis.camelot import to_camelot
from app.analysis.lookup import key_name
from app.db import queries, tracks
from app.deps import get_db
from app.routes.records import filters_from_query
from app.schemas import Page, Status, TrackHit, TrackOut, TrackPatch

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


@router.get("", response_model=Page[TrackHit])
def list_tracks(
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
    items, total = queries.list_tracks(conn, f)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{track_id}", response_model=TrackOut)
def get_track(track_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    detail = queries.track_detail(conn, track_id)
    if detail is None:
        raise HTTPException(404, "track not found")
    return detail


@router.patch("/{track_id}", response_model=TrackOut)
def patch_track(track_id: int, body: TrackPatch, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if tracks.get(conn, track_id) is None:
        raise HTTPException(404, "track not found")
    changes: dict = {}
    if body.bpm is not None:
        changes.update(bpm=body.bpm, bpm_manual=1)
    if body.key is not None:
        camelot = to_camelot(body.key)
        if camelot is None:
            raise HTTPException(422, f"unrecognised key '{body.key}' (use e.g. 'F# minor', 'Am' or '11A')")
        changes.update(key=key_name(camelot), camelot_key=camelot, key_manual=1)
    if "bpm" in body.unlock:
        changes["bpm_manual"] = 0
    if "key" in body.unlock:
        changes["key_manual"] = 0
    if "bpm" in body.unlock and body.bpm is not None or "key" in body.unlock and body.key is not None:
        raise HTTPException(422, "cannot set and unlock the same field in one request")
    tracks.update(conn, track_id, **changes)
    return queries.track_detail(conn, track_id)
