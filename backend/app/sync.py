"""The 'discogs_sync' job: add an owned record to the Discogs collection."""
import sqlite3
from collections.abc import Callable

from app.db import records
from app.discogs import DiscogsClient

JOB_TYPE = "discogs_sync"


def make_handler(discogs_factory: Callable[[], DiscogsClient]) -> Callable[[sqlite3.Connection, dict], dict]:
    def handler(conn: sqlite3.Connection, job: dict) -> dict:
        record = records.get(conn, job["record_id"])
        if record is None:
            raise ValueError("record no longer exists")
        if record["status"] != "owned":
            return {"skipped": f"status is '{record['status']}'; only owned records are collected"}
        if record["discogs_release_id"] is None:
            raise ValueError("record has no Discogs release id")
        instance_id, added = discogs_factory().add_to_collection(record["discogs_release_id"])
        records.update(conn, record["id"], discogs_collection_synced=1)
        return {"instance_id": instance_id, "added": added}

    return handler
