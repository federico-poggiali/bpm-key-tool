import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db import crate
from app.deps import get_db
from app.schemas import CrateOut, CubePatch, PlaceIn, SectionIn, UnitCreate, UnitPatch

router = APIRouter(prefix="/api/crate", tags=["crate"])


def _set(body) -> dict:
    return body.model_dump(exclude_none=True)


@router.get("", response_model=CrateOut)
def get_crate(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """The shelf: units, their cubes and sections with the records in each, and the unsorted
    records with a suggested section."""
    return crate.layout(conn)


@router.post("/units", response_model=CrateOut, status_code=201)
def create_unit(body: UnitCreate, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        crate.create_unit(conn, **body.model_dump())
    except crate.Overlap as exc:
        raise HTTPException(409, f"That spot is taken: {exc}") from exc
    return crate.layout(conn)


@router.patch("/units/{unit_id}", response_model=CrateOut)
def update_unit(unit_id: int, body: UnitPatch, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        found = crate.update_unit(conn, unit_id, **_set(body))
    except crate.Overlap as exc:
        raise HTTPException(409, f"That spot is taken: {exc}") from exc
    if not found:
        raise HTTPException(404, "unit not found")
    return crate.layout(conn)


@router.delete("/units/{unit_id}", status_code=204)
def delete_unit(unit_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    """Its records go back to unsorted."""
    if not crate.delete_unit(conn, unit_id):
        raise HTTPException(404, "unit not found")
    return Response(status_code=204)


@router.patch("/cubes/{cube_id}", response_model=CrateOut)
def update_cube(cube_id: int, body: CubePatch, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if not crate.update_cube(conn, cube_id, **_set(body)):
        raise HTTPException(404, "cube not found")
    return crate.layout(conn)


@router.post("/cubes/{cube_id}/sections", response_model=CrateOut, status_code=201)
def add_section(cube_id: int, body: SectionIn, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Add a divider: a new section at the right end of the cube."""
    if crate.add_section(conn, cube_id, body.name) is None:
        raise HTTPException(404, "cube not found")
    return crate.layout(conn)


@router.patch("/sections/{section_id}", response_model=CrateOut)
def update_section(section_id: int, body: SectionIn, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if not crate.update_section(conn, section_id, name=body.name):
        raise HTTPException(404, "section not found")
    return crate.layout(conn)


@router.delete("/sections/{section_id}", response_model=CrateOut)
def delete_section(section_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Remove a divider; its records merge into the neighbouring section."""
    result = crate.delete_section(conn, section_id)
    if result == "missing":
        raise HTTPException(404, "section not found")
    if result == "last":
        raise HTTPException(409, "A cube keeps at least one section")
    return crate.layout(conn)


@router.put("/place", response_model=CrateOut)
def place(body: PlaceIn, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """Put records in a section, or back in unsorted with section_id null."""
    if body.section_id is not None and not crate.section_exists(conn, body.section_id):
        raise HTTPException(404, "section not found")
    missing = crate.place(conn, body.record_ids, body.section_id)
    if missing:
        raise HTTPException(404, f"records not found: {missing}")
    return crate.layout(conn)
