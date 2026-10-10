"""Read queries behind the list/detail endpoints: filters, search and nested record data."""
import json
import re
import sqlite3
from dataclasses import dataclass, field

from app.db import notes as notes_dal
from app.db import records as records_dal
from app.db import tracks as tracks_dal


@dataclass
class Filters:
    bpm_min: float | None = None
    bpm_max: float | None = None
    camelot: str | None = None
    tags: list[str] = field(default_factory=list)
    status: str | None = None
    q: str | None = None
    limit: int = 50
    offset: int = 0

    @property
    def has_track_filter(self) -> bool:
        return any(v is not None for v in (self.bpm_min, self.bpm_max, self.camelot))


def fts_query(text: str | None) -> str | None:
    """Turn free text into a safe FTS5 query: every word must match, as a prefix."""
    tokens = re.findall(r"\w+", text or "")
    return " ".join(f'"{t}"*' for t in tokens) or None


def _track_conditions(f: Filters, alias: str) -> tuple[list[str], list]:
    where, params = [], []
    if f.bpm_min is not None:
        where.append(f"{alias}.bpm >= ?")
        params.append(f.bpm_min)
    if f.bpm_max is not None:
        where.append(f"{alias}.bpm <= ?")
        params.append(f.bpm_max)
    if f.camelot:
        where.append(f"{alias}.camelot_key = ?")
        params.append(f.camelot)
    return where, params


def _tag_exists(tag: str, record_expr: str, track_expr: str | None) -> tuple[str, list]:
    """A tag is satisfied by the record itself, or by one of its tracks."""
    sql = ("EXISTS (SELECT 1 FROM record_tags rt JOIN tags g ON g.id = rt.tag_id "
           f"WHERE rt.record_id = {record_expr} AND g.name = ?)")
    params = [tag]
    if track_expr:
        sql += (" OR EXISTS (SELECT 1 FROM track_tags tt JOIN tags g ON g.id = tt.tag_id "
                f"WHERE tt.track_id = {track_expr} AND g.name = ?)")
        params.append(tag)
    return f"({sql})", params


def _tags_for(conn: sqlite3.Connection, table: str, column: str, ids: list[int]) -> dict[int, list[str]]:
    if not ids:
        return {}
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT x.{column} AS id, g.name FROM {table} x JOIN tags g ON g.id = x.tag_id "
        f"WHERE x.{column} IN ({marks}) ORDER BY g.name", ids)
    out: dict[int, list[str]] = {}
    for r in rows:
        out.setdefault(r["id"], []).append(r["name"])
    return out


def _record_ref(r: dict) -> dict:
    return {k: r[k] for k in ("id", "artist", "title", "status", "cover_url")}


def list_records(conn: sqlite3.Connection, f: Filters) -> tuple[list[dict], int]:
    where: list[str] = []
    params: list = []
    if f.status:
        where.append("r.status = ?")
        params.append(f.status)
    if f.has_track_filter:
        conds, p = _track_conditions(f, "t")
        where.append("EXISTS (SELECT 1 FROM tracks t WHERE t.record_id = r.id AND "
                     + " AND ".join(conds) + ")")
        params += p
    for tag in f.tags:
        # tag on the record, or on any of its tracks
        sql, p = _tag_exists(tag, "r.id", None)
        sql_t = ("EXISTS (SELECT 1 FROM track_tags tt JOIN tags g ON g.id = tt.tag_id "
                 "JOIN tracks t ON t.id = tt.track_id WHERE t.record_id = r.id AND g.name = ?)")
        where.append(f"({sql} OR {sql_t})")
        params += p + [tag]
    if (match := fts_query(f.q)):
        where.append(
            "(r.id IN (SELECT rowid FROM records_fts WHERE records_fts MATCH ?) "
            "OR r.id IN (SELECT n.record_id FROM notes n WHERE n.record_id IS NOT NULL AND n.id IN "
            "(SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?)) "
            "OR r.id IN (SELECT t.record_id FROM notes n JOIN tracks t ON t.id = n.track_id WHERE n.id IN "
            "(SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?)))")
        params += [match] * 3
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    total = conn.execute(f"SELECT count(*) FROM records r {clause}", params).fetchone()[0]
    rows = [dict(r) for r in conn.execute(
        f"SELECT r.* FROM records r {clause} ORDER BY r.added_at DESC, r.id DESC LIMIT ? OFFSET ?",
        [*params, f.limit, f.offset])]

    ids = [r["id"] for r in rows]
    tags = _tags_for(conn, "record_tags", "record_id", ids)
    counts = {}
    if ids:
        marks = ",".join("?" for _ in ids)
        counts = {r[0]: r[1] for r in conn.execute(
            f"SELECT record_id, count(*) FROM tracks WHERE record_id IN ({marks}) GROUP BY record_id", ids)}
    for r in rows:
        r["tags"] = tags.get(r["id"], [])
        r["track_count"] = counts.get(r["id"], 0)
        r["matched_track_ids"] = None
        if f.has_track_filter:
            conds, p = _track_conditions(f, "t")
            r["matched_track_ids"] = [x[0] for x in conn.execute(
                "SELECT t.id FROM tracks t WHERE t.record_id = ? AND " + " AND ".join(conds)
                + " ORDER BY t.id",
                [r["id"], *p])]
    return rows, total


def _like(token: str) -> str:
    return "%" + token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def list_tracks(conn: sqlite3.Connection, f: Filters) -> tuple[list[dict], int]:
    where: list[str] = []
    params: list = []
    conds, p = _track_conditions(f, "t")
    where += conds
    params += p
    if f.status:
        where.append("r.status = ?")
        params.append(f.status)
    for tag in f.tags:  # on the track, or inherited from its record
        sql, p = _tag_exists(tag, "r.id", "t.id")
        where.append(sql)
        params += p
    if (match := fts_query(f.q)):
        words = re.findall(r"\w+", f.q)
        title_hit = " AND ".join("(t.title LIKE ? ESCAPE '\\' OR coalesce(t.artist, '') LIKE ? ESCAPE '\\')"
                                 for _ in words)
        where.append(
            f"(({title_hit}) "
            "OR t.id IN (SELECT n.track_id FROM notes n WHERE n.track_id IS NOT NULL AND n.id IN "
            "(SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?)) "
            "OR r.id IN (SELECT rowid FROM records_fts WHERE records_fts MATCH ?))")
        for w in words:
            params += [_like(w), _like(w)]
        params += [match, match]
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    base = f"FROM tracks t JOIN records r ON r.id = t.record_id {clause}"
    total = conn.execute(f"SELECT count(*) {base}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT t.*, r.artist AS r_artist, r.title AS r_title, r.status AS r_status, "
        f"r.cover_url AS r_cover FROM tracks t JOIN records r ON r.id = t.record_id {clause} "
        "ORDER BY r.id DESC, t.id LIMIT ? OFFSET ?", [*params, f.limit, f.offset]).fetchall()
    items = []
    for row in rows:
        d = dict(row)
        d["record"] = {"id": d["record_id"], "artist": d.pop("r_artist"), "title": d.pop("r_title"),
                       "status": d.pop("r_status"), "cover_url": d.pop("r_cover")}
        if d["analysis_raw"] is not None:
            d["analysis_raw"] = json.loads(d["analysis_raw"])
        items.append(d)
    ids = [d["id"] for d in items]
    tags = _tags_for(conn, "track_tags", "track_id", ids)
    for d in items:
        d["tags"] = tags.get(d["id"], [])
        d["notes"] = []
    return items, total


def track_detail(conn: sqlite3.Connection, track_id: int) -> dict | None:
    track = tracks_dal.get(conn, track_id)
    if track is None:
        return None
    track["tags"] = _tags_for(conn, "track_tags", "track_id", [track_id]).get(track_id, [])
    track["notes"] = notes_dal.list_for_track(conn, track_id)
    return track


def record_detail(conn: sqlite3.Connection, record_id: int) -> dict | None:
    record = records_dal.get(conn, record_id)
    if record is None:
        return None
    record["tags"] = _tags_for(conn, "record_tags", "record_id", [record_id]).get(record_id, [])
    record["notes"] = notes_dal.list_for_record(conn, record_id)
    track_rows = tracks_dal.list_for_record(conn, record_id)
    ids = [t["id"] for t in track_rows]
    tags = _tags_for(conn, "track_tags", "track_id", ids)
    track_notes: dict[int, list[dict]] = {}
    if ids:
        marks = ",".join("?" for _ in ids)
        for n in conn.execute(f"SELECT * FROM notes WHERE track_id IN ({marks}) ORDER BY id", ids):
            track_notes.setdefault(n["track_id"], []).append(dict(n))
    for t in track_rows:
        t["tags"] = tags.get(t["id"], [])
        t["notes"] = track_notes.get(t["id"], [])
    record["tracks"] = track_rows
    return record


def note_with_parents(conn: sqlite3.Connection, note: dict) -> dict:
    """A note plus the record (and track) it belongs to, for search results."""
    track = track_detail(conn, note["track_id"]) if note["track_id"] else None
    record = records_dal.get(conn, note["record_id"] if note["record_id"] else track["record_id"])
    return {"note": note, "record": _record_ref(record), "track": track}
