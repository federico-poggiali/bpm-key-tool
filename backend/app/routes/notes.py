import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db import notes, records, tracks
from app.deps import get_db, get_embedder
from app.embeddings import service
from app.embeddings.provider import EmbeddingProvider
from app.schemas import NoteCreate, NoteOut, NotePatch

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.post("", status_code=201, response_model=NoteOut)
def create_note(body: NoteCreate, conn: sqlite3.Connection = Depends(get_db),
                embedder: EmbeddingProvider | None = Depends(get_embedder)) -> dict:
    if (body.record_id is None) == (body.track_id is None):
        raise HTTPException(422, "a note belongs to exactly one of record_id or track_id")
    if body.record_id is not None and records.get(conn, body.record_id) is None:
        raise HTTPException(404, "record not found")
    if body.track_id is not None and tracks.get(conn, body.track_id) is None:
        raise HTTPException(404, "track not found")
    note_id = notes.create(conn, type=body.type.strip(), body=body.body,
                           record_id=body.record_id, track_id=body.track_id)
    service.sync_note(conn, embedder, note_id)
    return notes.get(conn, note_id)


@router.patch("/{note_id}", response_model=NoteOut)
def patch_note(note_id: int, body: NotePatch, conn: sqlite3.Connection = Depends(get_db),
               embedder: EmbeddingProvider | None = Depends(get_embedder)) -> dict:
    if notes.get(conn, note_id) is None:
        raise HTTPException(404, "note not found")
    changes = body.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise HTTPException(422, "type and body cannot be null")
    notes.update(conn, note_id, **changes)
    service.sync_note(conn, embedder, note_id)  # re-embeds on edit; drops it if no longer prose
    return notes.get(conn, note_id)


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    if not notes.delete(conn, note_id):
        raise HTTPException(404, "note not found")
    return Response(status_code=204)
