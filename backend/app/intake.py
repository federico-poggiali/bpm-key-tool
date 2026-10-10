import sqlite3
from dataclasses import dataclass

from app.db import queries, records, tracks
from app.discogs import DiscogsClient, release_to_record, release_to_tracks


@dataclass
class IntakeResult:
    record: dict
    created: bool
    resolved_from_master: int | None


def record_with_tracks(conn: sqlite3.Connection, record_id: int) -> dict:
    return queries.record_detail(conn, record_id)


def intake(conn: sqlite3.Connection, discogs: DiscogsClient, url: str,
           status: str = "owned") -> IntakeResult:
    release_id, master_id = discogs.resolve(url)
    existing = records.get_by_discogs_id(conn, release_id)
    if existing:
        return IntakeResult(record_with_tracks(conn, existing["id"]), False, master_id)
    data = discogs.release(release_id)
    record_id = records.create(conn, **release_to_record(data), status=status)
    for track in release_to_tracks(data):
        tracks.create(conn, record_id, **track)
    return IntakeResult(record_with_tracks(conn, record_id), True, master_id)
