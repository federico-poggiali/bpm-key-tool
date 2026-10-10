import sqlite3
from collections.abc import Iterator

from fastapi import HTTPException, Request

from app import config
from app.db import connect
from app.discogs import DiscogsClient, DiscogsError
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
