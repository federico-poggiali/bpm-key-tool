import sqlite3
from collections.abc import Iterator

from fastapi import HTTPException, Request

from app import config
from app.db import connect
from app.discogs import DiscogsClient, DiscogsError
from app.embeddings.provider import EmbeddingProvider, OpenAIProvider
from app.jobs.runner import JobRunner


def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def get_discogs() -> DiscogsClient:
    try:
        return DiscogsClient(config.DISCOGS_TOKEN)
    except DiscogsError as exc:
        raise HTTPException(503, str(exc)) from exc


def get_runner(request: Request) -> JobRunner:
    return request.app.state.runner


def get_embedder() -> EmbeddingProvider | None:
    """None when no OpenAI key is configured: notes still save, they just are not embedded."""
    if not config.OPENAI_API_KEY:
        return None
    return OpenAIProvider(config.OPENAI_API_KEY, config.EMBEDDING_MODEL)


def require_embedder() -> EmbeddingProvider:
    embedder = get_embedder()
    if embedder is None:
        raise HTTPException(503, "semantic search needs OPENAI_API_KEY in .env")
    return embedder
