import sqlite3

from fastapi import APIRouter, Depends

from app.db import queries
from app.deps import get_db
from app.schemas import StyleCount, StyleList

router = APIRouter(prefix="/api", tags=["styles"])


@router.get("/styles", response_model=StyleList)
def list_styles(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Every style in the library with its record count, for filter and editor pickers."""
    return {"items": [StyleCount(**s) for s in queries.style_counts(conn)]}
