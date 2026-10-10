import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import queries
from app.deps import get_db, require_embedder
from app.embeddings import service
from app.embeddings.provider import EmbeddingError, EmbeddingProvider
from app.schemas import ExactResults, ReembedOut, SemanticHit

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search/exact", response_model=ExactResults)
def exact(q: Annotated[str, Query(min_length=1)], limit: Annotated[int, Query(ge=1, le=100)] = 20,
          conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return queries.exact_search(conn, q, limit)


@router.get("/search/semantic", response_model=list[SemanticHit])
def semantic(q: Annotated[str, Query(min_length=1)], limit: Annotated[int, Query(ge=1, le=100)] = 20,
             conn: sqlite3.Connection = Depends(get_db),
             embedder: EmbeddingProvider = Depends(require_embedder)) -> list[dict]:
    try:
        return service.semantic_search(conn, embedder, q, limit)
    except EmbeddingError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/admin/reembed", response_model=ReembedOut)
def reembed(conn: sqlite3.Connection = Depends(get_db),
            embedder: EmbeddingProvider = Depends(require_embedder)) -> dict[str, int]:
    try:
        return {"embedded": service.reembed_all(conn, embedder)}
    except EmbeddingError as exc:
        raise HTTPException(502, str(exc)) from exc
