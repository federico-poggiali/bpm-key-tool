import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import queries
from app.deps import get_db
from app.labels import data as label_data
from app.labels.api import LabelRender, draw
from app.labels.data import LabelData

router = APIRouter(prefix="/api/records/{record_id}/label", tags=["labels"])


@router.get("", response_model=LabelData)
def get_label(record_id: int, conn: sqlite3.Connection = Depends(get_db)) -> LabelData:
    """The label as the database describes it: the starting point for the editor."""
    detail = queries.record_detail(conn, record_id)
    if detail is None:
        raise HTTPException(404, "record not found")  # a label only exists for a record in the library
    return label_data.build(detail)


@router.post("/render", response_model=LabelRender)
def render_label(record_id: int, body: LabelData, conn: sqlite3.Connection = Depends(get_db)) -> LabelRender:
    """Draw the (possibly edited) label. Nothing is stored: edits apply to this print only."""
    if queries.record_detail(conn, record_id) is None:
        raise HTTPException(404, "record not found")
    return draw(body)
