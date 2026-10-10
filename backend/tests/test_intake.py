from app.db import tracks
from app.db.connection import connect
from tests.conftest import load_fixture


def count_rows(table):
    conn = connect()
    try:
        return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_intake_creates_record_and_tracks(client):
    resp = client.post("/api/records/intake",
                       json={"discogs_url": "https://www.discogs.com/release/9261843-x"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["artist"] == "Truncate"
    assert body["status"] == "owned"
    assert body["resolved_from_master"] is None
    assert [t["position"] for t in body["tracks"]] == ["A1", "A2", "B"]
    assert count_rows("records") == 1
    assert count_rows("tracks") == 3


def test_intake_twice_does_not_duplicate(client, discogs_calls):
    url = {"discogs_url": "https://www.discogs.com/release/9261843"}
    first = client.post("/api/records/intake", json=url)
    again = client.post("/api/records/intake", json=url)
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json()["id"] == first.json()["id"]
    assert count_rows("records") == 1 and count_rows("tracks") == 3
    assert discogs_calls.count("/releases/9261843") == 1  # second call never refetches


def test_intake_master_resolves_to_main_release(client):
    resp = client.post("/api/records/intake", json={"discogs_url": "https://www.discogs.com/master/137924"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["resolved_from_master"] == 137924
    assert body["discogs_release_id"] == 12472
    n_expected = len([t for t in load_fixture("release_cd.json")["tracklist"] if t["type_"] == "track"])
    assert len(body["tracks"]) == n_expected
    assert {"C1"} <= {t["position"] for t in body["tracks"]}
    assert all(t["artist"] for t in body["tracks"])


def test_intake_status_and_errors(client):
    ok = client.post("/api/records/intake",
                     json={"discogs_url": "https://www.discogs.com/release/46673", "status": "wantlist"})
    assert ok.json()["status"] == "wantlist"
    assert client.post("/api/records/intake", json={"discogs_url": "https://x.com/y"}).status_code == 400
    assert client.post("/api/records/intake",
                       json={"discogs_url": "https://www.discogs.com/release/999"}).status_code == 404
    assert client.post("/api/records/intake",
                       json={"discogs_url": "https://www.discogs.com/release/1", "status": "bad"}
                       ).status_code == 422
    conn = connect()
    assert tracks.list_for_record(conn, ok.json()["id"])[0]["title"].startswith("Be Brave")
    conn.close()
