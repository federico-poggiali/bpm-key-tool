import sqlite3

import pytest

from app.db import connect, migrate, notes, records, tags, tracks
from app.db.migrate import MIGRATIONS_DIR


@pytest.fixture
def conn():
    c = connect(":memory:")
    migrate(c)
    yield c
    c.close()


@pytest.fixture
def record(conn):
    rid = records.create(conn, artist="Daft Punk", title="Discovery", label="Virgin",
                         year=2001, discogs_release_id=123)
    t1 = tracks.create(conn, rid, position="A1", title="One More Time", duration_sec=320)
    t2 = tracks.create(conn, rid, position="A2", title="Aerodynamic")
    return rid, t1, t2


def test_migrate_is_idempotent(conn):
    latest = len(list(MIGRATIONS_DIR.glob("*.sql")))
    assert migrate(conn) == latest
    assert conn.execute("SELECT count(*) FROM schema_version").fetchone()[0] == latest


def test_record_and_tracks_crud(conn, record):
    rid, t1, _ = record
    assert records.get(conn, rid)["status"] == "owned"
    assert records.get_by_discogs_id(conn, 123)["id"] == rid
    assert [t["position"] for t in tracks.list_for_record(conn, rid)] == ["A1", "A2"]
    tracks.update(conn, t1, bpm=123.0, analysis_raw={"bpm_alt": 61.5})
    assert tracks.get(conn, t1)["analysis_raw"] == {"bpm_alt": 61.5}
    records.update(conn, rid, status="wantlist")
    assert records.get(conn, rid)["status"] == "wantlist"
    with pytest.raises(ValueError):
        records.update(conn, rid, id=99)


def test_invalid_status_and_duplicate_release_rejected(conn, record):
    with pytest.raises(sqlite3.IntegrityError):
        records.create(conn, artist="x", title="y", status="bogus")
    with pytest.raises(sqlite3.IntegrityError):
        records.create(conn, artist="x", title="y", discogs_release_id=123)


def test_notes_record_and_track_level(conn, record):
    rid, t1, _ = record
    n1 = notes.create(conn, type="location", body="Shelf B", record_id=rid)
    n2 = notes.create(conn, type="prose", body="huge energy", track_id=t1)
    assert [n["id"] for n in notes.list_for_record(conn, rid)] == [n1]
    assert [n["id"] for n in notes.list_for_track(conn, t1)] == [n2]


def test_note_requires_exactly_one_parent(conn, record):
    rid, t1, _ = record
    with pytest.raises(sqlite3.IntegrityError):
        notes.create(conn, type="prose", body="none")
    with pytest.raises(sqlite3.IntegrityError):
        notes.create(conn, type="prose", body="both", record_id=rid, track_id=t1)


def test_embeddings_only_for_prose_and_cleaned_up(conn, record):
    rid, _, _ = record
    vec = [0.1] * 1536
    prose = notes.create(conn, type="prose", body="banging", record_id=rid)
    other = notes.create(conn, type="location", body="Shelf", record_id=rid)
    notes.set_embedding(conn, prose, vec)
    with pytest.raises(ValueError):
        notes.set_embedding(conn, other, vec)
    with pytest.raises(ValueError):
        notes.set_embedding(conn, prose, [0.1] * 3)
    assert notes.has_embedding(conn, prose)
    notes.update(conn, prose, type="location")
    assert not notes.has_embedding(conn, prose)
    notes.update(conn, prose, type="prose")
    notes.set_embedding(conn, prose, vec)
    notes.delete(conn, prose)
    assert not notes.has_embedding(conn, prose)


def test_tags(conn, record):
    rid, t1, _ = record
    tags.add(conn, "record", rid, " House ")
    tags.add(conn, "record", rid, "house")
    tags.add(conn, "track", t1, "House")
    tags.add(conn, "track", t1, "peak")
    assert tags.for_item(conn, "record", rid) == ["house"]
    assert tags.for_item(conn, "track", t1) == ["house", "peak"]
    counts = {t["name"]: t for t in tags.list_with_counts(conn)}
    assert counts["house"]["record_count"] == 1 and counts["house"]["track_count"] == 1
    assert tags.remove(conn, "track", t1, "peak")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO tags(name) VALUES ('UPPER')")


def test_full_text_search_tracks_changes(conn, record):
    rid, _, _ = record
    assert [r["id"] for r in records.search(conn, "daft")] == [rid]
    records.update(conn, rid, artist="Justice")
    assert records.search(conn, "daft") == []
    assert [r["id"] for r in records.search(conn, "justice")] == [rid]
    nid = notes.create(conn, type="prose", body="floor erupted", record_id=rid)
    assert [n["id"] for n in notes.search(conn, "erupted")] == [nid]
    notes.update(conn, nid, body="calm")
    assert notes.search(conn, "erupted") == []
    notes.delete(conn, nid)
    assert notes.search(conn, "calm") == []


def test_cascade_delete(conn, record):
    rid, t1, _ = record
    notes.create(conn, type="prose", body="x", track_id=t1)
    tags.add(conn, "track", t1, "a")
    records.delete(conn, rid)
    assert tracks.get(conn, t1) is None
    assert conn.execute("SELECT count(*) FROM notes").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM track_tags").fetchone()[0] == 0
    assert records.search(conn, "daft") == []
