import base64
import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import queries
from app.deps import get_db
from app.labels import data as label_data
from app.labels import render as label_render
from app.labels.data import LabelData

router = APIRouter(prefix="/api/records/{record_id}/label", tags=["labels"])


class LabelImage(BaseModel):
    kind: Literal["main", "tracks"]
    name: str  # "main", "tracks", or "tracks-2" when the tracklist needs several labels
    png_base64: str  # 1-bit PNG, 696 px wide (62 mm at 300 dpi): what the Brother QL prints
    width: int
    height: int


class LabelRender(BaseModel):
    images: list[LabelImage]
    warnings: list[str]


def draw(data: LabelData) -> LabelRender:
    images, warnings = label_render.render(data)
    return LabelRender(
        images=[LabelImage(kind=i.kind, name=i.name, png_base64=base64.b64encode(i.png).decode(),
                           width=label_render.W, height=label_render.H) for i in images],
        warnings=warnings)


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
