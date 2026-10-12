import pytest

from app import backfill
from app.db import connect, records, tracks
from app.jobs.runner import JobRunner
from tests.conftest import make_discogs


@pytest.fixture
def library(db_path):
    conn = connect(db_path)
    house = records.create(conn, artist="Daft Punk", title="Discovery", discogs_release_id=1,
                           year=1997, styles=["Deep House", "Disco"])
    h1 = tracks.create(conn, house, position="A1", title="One More Time", bpm=123.0, camelot_key="4A",
                       key="F minor")
    tracks.create(conn, house, position="A2", title="Aerodynamic", bpm=140.0, camelot_key="9A")
    techno = records.create(conn, artist="Jeff Mills", title="The Bells", discogs_release_id=2,
                            year=1994, styles=["Techno", "Dub Techno"])
    t1 = tracks.create(conn, techno, position="A", title="The Bells", bpm=135.0, camelot_key="4A",
                       key="F minor")
    bare = records.create(conn, artist="Old", title="Record", discogs_release_id=3)  # never fetched
    tracks.create(conn, bare, position="A", title="x", bpm=124.0)
    conn.close()
    return {"house": house, "techno": techno, "bare": bare, "h1": h1, "t1": t1}


def ids(resp):
    assert resp.status_code == 200, resp.text
    return [i["id"] for i in resp.json()["items"]]


def test_style_filter_is_case_insensitive_and_requires_all(client, library):
    assert ids(client.get("/api/records?style=deep house")) == [library["house"]]
    assert ids(client.get("/api/records?style=TECHNO")) == [library["techno"]]
    assert ids(client.get("/api/records?style=Techno&style=dub%20techno")) == [library["techno"]]
    assert ids(client.get("/api/records?style=Techno&style=Disco")) == []


def test_style_filter_combines_with_bpm_key_and_tags(client, library, db_path):
    from app.db import tags
    conn = connect(db_path)
    tags.create_tag(conn, 2, "french")
    tags.add(conn, "record", library["house"], "french")
    conn.close()
    assert ids(client.get("/api/records?style=Disco&bpm_min=120&bpm_max=125")) == [library["house"]]
    assert ids(client.get("/api/records?style=Disco&bpm_min=130")) == [library["house"]]  # 140 BPM track
    assert ids(client.get("/api/records?style=Disco&key=4A&tag=french")) == [library["house"]]
    assert ids(client.get("/api/records?style=Disco&key=4A&tag=peak")) == []
    assert ids(client.get("/api/records?style=Techno&key=4A")) == [library["techno"]]


def test_tracks_inherit_styles_and_filter_through_their_record(client, library):
    body = client.get("/api/tracks?style=Disco").json()
    assert body["total"] == 2
    assert all(t["styles"] == ["Deep House", "Disco"] for t in body["items"])
    assert client.get(f"/api/tracks/{library['t1']}").json()["styles"] == ["Techno", "Dub Techno"]
    detail = client.get(f"/api/records/{library['house']}").json()
    assert [t["styles"] for t in detail["tracks"]] == [["Deep House", "Disco"]] * 2
    assert [t["year"] for t in detail["tracks"]] == [1997, 1997]  # the record's year, on every track
    assert client.get(f"/api/tracks/{library['t1']}").json()["year"] == 1994
    assert {t["year"] for t in body["items"]} == {1997}
    assert client.get(f"/api/records/{library['bare']}").json()["styles"] == []  # never fetched reads as empty


def test_styles_endpoint_counts_case_insensitively(client, library, db_path):
    conn = connect(db_path)
    records.create(conn, artist="X", title="Y", styles=["techno"])
    conn.close()
    items = {i["name"].lower(): i["record_count"] for i in client.get("/api/styles").json()["items"]}
    assert items == {"techno": 2, "dub techno": 1, "deep house": 1, "disco": 1}


def test_patch_edits_styles_and_locks_them(client, library):
    resp = client.patch(f"/api/records/{library['house']}",
                        json={"styles": ["  Italo Disco ", "italo disco", "House"]})
    body = resp.json()
    assert body["styles"] == ["Italo Disco", "House"] and body["styles_manual"] is True
    assert body["tracks"][0]["styles"] == ["Italo Disco", "House"]
    assert ids(client.get("/api/records?style=italo disco")) == [library["house"]]
    assert client.patch(f"/api/records/{library['house']}", json={"styles": None}).status_code == 422
    assert client.patch(f"/api/records/{library['house']}",
                        json={"styles": ["a"], "reset_styles": True}).status_code == 422


def test_reset_releases_the_lock_and_refetches(client, db_path):
    conn = connect(db_path)
    rid = records.create(conn, artist="Truncate", title="7", discogs_release_id=9261843)
    conn.close()
    client.patch(f"/api/records/{rid}", json={"styles": ["Mine"]})
    body = client.patch(f"/api/records/{rid}", json={"reset_styles": True}).json()
    assert body["styles"] == ["Acid", "Techno"] and body["styles_manual"] is False


def test_reset_needs_a_discogs_release(client, library, db_path):
    conn = connect(db_path)
    rid = records.create(conn, artist="Local", title="Only")
    conn.close()
    assert client.patch(f"/api/records/{rid}", json={"reset_styles": True}).status_code == 400


def test_backfill_fills_only_unfetched_unedited_records(client, db_path, discogs_calls):
    conn = connect(db_path)
    old = records.create(conn, artist="Truncate", title="7", discogs_release_id=9261843)
    edited = records.create(conn, artist="R&S", title="x", discogs_release_id=46673,
                            styles=["Mine"], styles_manual=1)
    empty = records.create(conn, artist="E", title="e", discogs_release_id=12472, styles=[])
    missing = records.create(conn, artist="M", title="m", discogs_release_id=999)  # Discogs 404
    conn.close()

    runner = JobRunner({backfill.JOB_TYPE: backfill.make_handler(lambda: make_discogs(discogs_calls))})
    client.app.state.runner = runner
    job_id = client.post("/api/admin/backfill-styles").json()["job_id"]
    runner.run_pending()
    result = client.get(f"/api/jobs/{job_id}").json()["result"]
    assert result["updated"] == 1 and [f["record_id"] for f in result["failed"]] == [missing]

    conn = connect(db_path)
    assert records.get(conn, old)["styles"] == ["Acid", "Techno"]
    assert records.get(conn, old)["catno"] == "TRUNCATE14"
    assert records.get(conn, edited)["styles"] == ["Mine"]
    assert records.get(conn, empty)["styles"] == []
    assert records.get(conn, missing)["styles"] is None
    assert discogs_calls.count("/releases/9261843") == 1 and "/releases/46673" not in discogs_calls

    discogs_calls.clear()  # a second run only retries what is still unfetched
    assert backfill.backfill_styles(conn, make_discogs(discogs_calls))["updated"] == 0
    assert discogs_calls == ["/releases/999"]
    conn.close()
