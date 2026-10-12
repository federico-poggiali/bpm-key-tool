"""Labels for records that are not in the library: blank, or fetched from a pasted Discogs link."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import queries, records
from app.deps import get_db, get_discogs
from app.discogs import DiscogsClient, DiscogsError, DiscogsNotFound, release_to_record, release_to_tracks
from app.labels import data as label_data
from app.labels.data import LabelData
from app.routes.labels import LabelRender, draw

router = APIRouter(prefix="/api/labels", tags=["labels"])


class FromDiscogs(BaseModel):
    discogs_url: str


@router.post("/from-discogs", response_model=LabelData)
def label_from_discogs(body: FromDiscogs, conn: sqlite3.Connection = Depends(get_db),
                       discogs: DiscogsClient = Depends(get_discogs)) -> LabelData:
    """Look a release up and describe it as a label. Nothing is stored; a record already in the
    library brings its BPM, key, tags and notes along."""
    try:
        release_id, _ = discogs.resolve(body.discogs_url)
        existing = records.get_by_discogs_id(conn, release_id)
        if existing:
            return label_data.build(queries.record_detail(conn, existing["id"]))
        release = discogs.release(release_id)
    except DiscogsNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except DiscogsError as exc:
        raise HTTPException(400 if "Not a Discogs" in str(exc) else 502, str(exc)) from exc
    record = release_to_record(release)
    return label_data.build({
        **record, "notes": [],
        "tracks": [{**t, "bpm": None, "key": None, "camelot_key": None, "tags": [], "notes": []}
                   for t in release_to_tracks(release)],
    })


@router.post("/render", response_model=LabelRender)
def render_loose_label(body: LabelData) -> LabelRender:
    """Draw a label that belongs to no record. Nothing is stored."""
    return draw(body)
