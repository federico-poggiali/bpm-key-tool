import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import records, tags, tracks
from app.deps import get_db
from app.schemas import GroupIn, GroupList, GroupRename, TagCount, TagDefIn, TagDefUpdate, TagIn, TagList

router = APIRouter(prefix="/api", tags=["tags"])


@router.get("/tags", response_model=TagList)
def list_tags(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"items": [TagCount(**t) for t in tags.list_with_counts(conn)]}


def _guard(call, *args, **kwargs):
    """Map the data layer's errors onto HTTP: unknown -> 404, fixed group -> 403, bad input -> 422."""
    try:
        return call(*args, **kwargs)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


# ---- the Tag Manager ----

@router.get("/tag-groups", response_model=GroupList)
def list_groups(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"items": tags.list_groups(conn)}


@router.post("/tag-groups", status_code=201, response_model=GroupList)
def create_group(body: GroupIn, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    _guard(tags.create_group, conn, body.name)
    return {"items": tags.list_groups(conn)}


@router.patch("/tag-groups/{group_id}", response_model=GroupList)
def rename_group(group_id: int, body: GroupRename, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    _guard(tags.rename_group, conn, group_id, body.name)
    return {"items": tags.list_groups(conn)}


@router.delete("/tag-groups/{group_id}", response_model=GroupList)
def delete_group(group_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    _guard(tags.delete_group, conn, group_id)
    return {"items": tags.list_groups(conn)}


@router.post("/tag-groups/{group_id}/tags", status_code=201, response_model=GroupList)
def create_tag(group_id: int, body: TagDefIn, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    _guard(tags.create_tag, conn, group_id, body.name)
    return {"items": tags.list_groups(conn)}


@router.patch("/tag-defs/{tag_id}", response_model=GroupList)
def update_tag(tag_id: int, body: TagDefUpdate, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    _guard(tags.update_tag, conn, tag_id, body.name, body.group_id)
    return {"items": tags.list_groups(conn)}


@router.delete("/tag-defs/{tag_id}", response_model=GroupList)
def delete_tag(tag_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    _guard(tags.delete_tag, conn, tag_id)
    return {"items": tags.list_groups(conn)}


# ---- tags on records and tracks ----

def _check(conn: sqlite3.Connection, kind: str, item_id: int) -> None:
    exists = records.get(conn, item_id) if kind == "record" else tracks.get(conn, item_id)
    if exists is None:
        raise HTTPException(404, f"{kind} not found")


def _add(kind: str):
    def add(item_id: int, body: TagIn, conn: sqlite3.Connection = Depends(get_db)) -> list[str]:
        _check(conn, kind, item_id)
        _guard(tags.add, conn, kind, item_id, body.name)
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
