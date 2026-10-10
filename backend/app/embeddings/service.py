"""Keeps prose-note embeddings in step with the notes, and answers meaning-based queries."""
import logging
import math
import sqlite3
import struct

from app.db import notes, queries
from app.embeddings.provider import DIMENSIONS, EmbeddingError, EmbeddingProvider

log = logging.getLogger(__name__)


def _unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def sync_note(conn: sqlite3.Connection, provider: EmbeddingProvider | None, note_id: int) -> None:
    """Embed a prose note, or drop the embedding if it is not (or no longer) prose.

    A failing provider never loses the note: the embedding is simply missing until the next
    save or a reembed.
    """
    note = notes.get(conn, note_id)
    if note is None or note["type"] != notes.PROSE:
        notes.delete_embedding(conn, note_id)
        return
    if provider is None:
        return
    try:
        (vector,) = provider.embed([note["body"]])
    except EmbeddingError as exc:
        log.warning("could not embed note %s: %s", note_id, exc)
        return
    notes.set_embedding(conn, note_id, _unit(vector))


def reembed_all(conn: sqlite3.Connection, provider: EmbeddingProvider) -> int:
    """Rebuild every embedding (needed when the model changes). Returns how many notes."""
    prose = [dict(r) for r in conn.execute(
        "SELECT id, body FROM notes WHERE type = ? ORDER BY id", (notes.PROSE,))]
    vectors = provider.embed([n["body"] for n in prose]) if prose else []
    conn.execute("DELETE FROM note_embeddings")
    conn.commit()
    for n, vector in zip(prose, vectors, strict=True):
        notes.set_embedding(conn, n["id"], _unit(vector))
    return len(prose)


def semantic_search(conn: sqlite3.Connection, provider: EmbeddingProvider, query: str,
                    limit: int = 20) -> list[dict]:
    (vector,) = provider.embed([query])
    blob = struct.pack(f"{DIMENSIONS}f", *_unit(vector))
    rows = conn.execute(
        "SELECT note_id, distance FROM note_embeddings WHERE embedding MATCH ? AND k = ? "
        "ORDER BY distance", (blob, limit)).fetchall()
    hits = []
    for row in rows:
        note = notes.get(conn, row["note_id"])
        if note is None:
            continue
        # unit vectors: cosine similarity = 1 - L2^2 / 2
        score = max(0.0, 1.0 - row["distance"] ** 2 / 2)
        hits.append({"score": round(score, 4), **queries.note_with_parents(conn, note)})
    return hits
