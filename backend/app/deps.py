import sqlite3
from collections.abc import Callable, Iterator

from fastapi import HTTPException, Request

from app import config
from app.db import connect
from app.discogs import DiscogsClient, DiscogsError
from app.embeddings.provider import EmbeddingProvider
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


def get_discogs_lazy(request: Request) -> Callable[[], DiscogsClient]:
    """The Discogs client factory, called only if a request needs Discogs (a missing token is
    then a 503 for that request alone). Honours test overrides of get_discogs."""
    return request.app.dependency_overrides.get(get_discogs, get_discogs)


def get_runner(request: Request) -> JobRunner:
    return request.app.state.runner


def get_embedder() -> EmbeddingProvider | None:
    """The configured embedding provider. None until one is wired in: notes still save, they just
    are not embedded. This is the single place to plug a local or hosted model in later."""
    return None


def require_embedder() -> EmbeddingProvider:
    embedder = get_embedder()
    if embedder is None:
        raise HTTPException(503, "semantic search is not available: no embedding provider is configured")
    return embedder
