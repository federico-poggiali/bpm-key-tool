import time
from pathlib import Path

import pytest

from app.db import connect, notes, queries, records, tags, tracks
from app.vault import EXAMPLES_FILE, RECORDS_SUBDIR, VaultSyncer, filename_for, render_record, sync_vault

EXPECTED = Path(__file__).parent / "fixtures" / "vault_expected.md"


@pytest.fixture
def conn(db_path):
    c = connect(db_path)
    yield c
    c.close()


@pytest.fixture
def fixture_record(conn):
    rid = records.create(
        conn, artist="Daft Punk", title="Discovery", label="Virgin", year=2001, format="2xVinyl, LP",
        discogs_release_id=123, cover_url="https://img.example/cover.jpg",
        catno="V2850", styles=["French House", "Disco"])
    t1 = tracks.create(conn, rid, position="A1", title="One More Time", bpm=123.0, key="F minor",
                       camelot_key="4A", confidence=0.62, bpm_manual=1)
    tracks.create(conn, rid, position="A2", title="Aero | dynamic", bpm=123.5, key="E minor",
                  camelot_key="9A", confidence=0.4)
    tracks.create(conn, rid, position="B1", title="Digital Love", artist="Guest")
    tags.create_tag(conn, 2, "french")
    tags.create_tag(conn, 2, "house")
    tags.add(conn, "record", rid, "french")
    tags.add(conn, "record", rid, "house")
    notes.create(conn, type="location", body="Shelf B, second row", record_id=rid)
    notes.create(conn, type="prose", body="Huge energy,\nthe floor erupted.", track_id=t1)
    return rid


def test_snapshot_of_generated_markdown(conn, fixture_record):
    markdown = render_record(queries.record_detail(conn, fixture_record))
    if not EXPECTED.exists():
        EXPECTED.write_text(markdown, encoding="utf-8")
    assert markdown == EXPECTED.read_text(encoding="utf-8")


def test_sync_writes_skips_and_deletes(conn, fixture_record, tmp_path):
    vault = tmp_path / "vault"
    first = sync_vault(conn, vault)
    assert (first.written, first.skipped, first.deleted) == (2, 0, 0)  # the record + Dataview examples
    note = vault / RECORDS_SUBDIR / "Daft Punk - Discovery (123).md"
    assert note.exists() and (vault / EXAMPLES_FILE).exists()
    assert "```dataview" in (vault / EXAMPLES_FILE).read_text()

    mtime = note.stat().st_mtime_ns
    second = sync_vault(conn, vault)
    assert (second.written, second.skipped) == (0, 2) and note.stat().st_mtime_ns == mtime

    note.write_text("edited in Obsidian")  # edits are discarded
    assert sync_vault(conn, vault).written == 1
    assert "Shelf B" in note.read_text()

    records.update(conn, fixture_record, title="Discovery (Remastered)")  # rename: old file goes
    third = sync_vault(conn, vault)
    assert third.deleted == 1 and not note.exists()
    assert (vault / RECORDS_SUBDIR / "Daft Punk - Discovery (Remastered) (123).md").exists()

    records.delete(conn, fixture_record)
    assert sync_vault(conn, vault).deleted == 1
    assert list((vault / RECORDS_SUBDIR).glob("*.md")) == []


def test_only_generated_files_are_deleted(conn, tmp_path):
    vault = tmp_path / "vault"
    (vault / RECORDS_SUBDIR).mkdir(parents=True)
    mine = vault / RECORDS_SUBDIR / "My own note.md"
    mine.write_text("# keep me")
    sync_vault(conn, vault)
    assert mine.exists()


def test_wantlist_gets_its_own_file_with_status(conn, tmp_path):
    rid = records.create(conn, artist="Model 500", title="Be Brave", status="wantlist")
    sync_vault(conn, tmp_path)
    text = (tmp_path / RECORDS_SUBDIR / f"Model 500 - Be Brave (local-{rid}).md").read_text()
    assert 'status: "wantlist"' in text and "discogs_id: null" in text


def test_filenames_are_safe():
    record = {"id": 1, "discogs_release_id": 9, "artist": 'AC/DC', "title": 'Who: "Made" Who?'}
    assert filename_for(record) == "AC-DC - Who- -Made- Who (9).md"


def test_frontmatter_ranges(conn, fixture_record):
    text = render_record(queries.record_detail(conn, fixture_record))
    for line in ('bpm_min: 123.0', 'bpm_max: 123.5', 'camelot_keys: ["4A", "9A"]',
                 'keys: ["E minor", "F minor"]', 'tags: ["french", "house"]'):
        assert line in text


def test_syncer_debounces_and_endpoints(client, db_path, tmp_path):
    vault = tmp_path / "debounced"
    syncer = VaultSyncer(vault, delay=0.15)
    conn = connect(db_path)
    records.create(conn, artist="A", title="B", discogs_release_id=5)
    conn.close()
    for _ in range(5):
        syncer.request()  # a burst of writes coalesces into one sync
    assert not vault.exists()
    deadline = time.time() + 3
    while syncer.last_result is None and time.time() < deadline:
        time.sleep(0.05)
    assert syncer.last_result["written"] == 2

    client.app.state.vault_syncer = syncer
    try:
        assert client.get("/api/admin/vault-status").json()["last_sync"]["written"] == 2
        again = client.post("/api/admin/sync-vault").json()
        assert (again["written"], again["skipped"]) == (0, 2)
    finally:
        del client.app.state.vault_syncer


def test_writes_through_the_api_request_a_sync(client):
    class Spy:
        calls = 0

        def request(self):
            Spy.calls += 1

    client.app.state.vault_syncer = Spy()
    try:
        client.get("/api/records")
        assert Spy.calls == 0  # reads do nothing
        client.post("/api/notes", json={"type": "a", "body": "x"})  # rejected (422): no sync
        assert Spy.calls == 0
        rid = None
        from app.db import connect as c
        conn = c()
        rid = records.create(conn, artist="A", title="B")
        conn.close()
        client.patch(f"/api/records/{rid}", json={"year": 2000})
        assert Spy.calls == 1
    finally:
        del client.app.state.vault_syncer


def test_sync_endpoint_unavailable_without_syncer(client):
    assert client.post("/api/admin/sync-vault").status_code == 503
