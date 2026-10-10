import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import records, tags, tracks
from app.deps import get_db
from app.schemas import TagCount, TagIn, TagList

router = APIRouter(prefix="/api", tags=["tags"])


@router.get("/tags", response_model=TagList)
def list_tags(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"items": [TagCount(**t) for t in tags.list_with_counts(conn)]}


def _check(conn: sqlite3.Connection, kind: str, item_id: int) -> None:
    exists = records.get(conn, item_id) if kind == "record" else tracks.get(conn, item_id)
    if exists is None:
        raise HTTPException(404, f"{kind} not found")


def _add(kind: str):
    def add(item_id: int, body: TagIn, conn: sqlite3.Connection = Depends(get_db)) -> list[str]:
        _check(conn, kind, item_id)
        tags.add(conn, kind, item_id, body.name)
        return tags.for_item(conn, kind, item_id)
    return add


def _remove(kind: str):
    def remove(item_id: int, name: str, conn: sqlite3.Connection = Depends(get_db)) -> list[str]:
        _check(conn, kind, item_id)
        if not tags.remove(conn, kind, item_id, name):
            raise HTTPException(404, "tag not on this item")
        return tags.for_item(conn, kind, item_id)
    return remove


for _kind, _plural in (("record", "records"), ("track", "tracks")):
    router.add_api_route(f"/{_plural}/{{item_id}}/tags", _add(_kind), methods=["POST"],
                         status_code=201, name=f"add_{_kind}_tag", response_model=list[str])
    router.add_api_route(f"/{_plural}/{{item_id}}/tags/{{name}}", _remove(_kind), methods=["DELETE"],
                         name=f"remove_{_kind}_tag", response_model=list[str])
