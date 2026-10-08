from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

from . import config
from .models import Measurement, Track


class Cache:
    """Measurements per (Discogs release, track position). Row present => lookups already done."""

    def __init__(self, path=config.CACHE_PATH):
        self.db = sqlite3.connect(path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS tracks (release_id INTEGER, position TEXT, "
            "artist TEXT, title TEXT, measurements TEXT, PRIMARY KEY (release_id, position))"
        )

    def get(self, track: Track) -> list[Measurement] | None:
        row = self.db.execute(
            "SELECT artist, title, measurements FROM tracks WHERE release_id=? AND position=?",
            (track.release_id, track.position)).fetchone()
        if not row or (row[0], row[1]) != (track.artist, track.title):
            return None  # missing, or the tracklist was edited on Discogs
        return [Measurement(**d) for d in json.loads(row[2])]

    def put(self, track: Track) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO tracks VALUES (?,?,?,?,?)",
            (track.release_id, track.position, track.artist, track.title,
             json.dumps([asdict(m) for m in track.measurements])))
        self.db.commit()

    def close(self) -> None:
        self.db.close()
