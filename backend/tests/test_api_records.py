import pytest

from app.db import connect, jobs, records, tags, tracks


@pytest.fixture
def library(db_path):
    """Three records: a house record with two tracks, a techno one, and a wantlist one."""
    conn = connect(db_path)
    house = records.create(conn, artist="Daft Punk", title="Discovery", label="Virgin",
                           year=2001, discogs_release_id=1)
    h1 = tracks.create(conn, house, position="A1", title="One More Time", bpm=123.0, camelot_key="4A",
                       key="F minor")
    h2 = tracks.create(conn, house, position="A2", title="Aerodynamic", bpm=123.5, camelot_key="9A",
                       key="E minor")
    techno = records.create(conn, artist="Jeff Mills", title="The Bells", discogs_release_id=2)
    t1 = tracks.create(conn, techno, position="A", title="The Bells", bpm=135.0, camelot_key="4A",
                       key="F minor")
    want = records.create(conn, artist="Model 500", title="Be Brave", status="wantlist",
                          discogs_release_id=3)
    w1 = tracks.create(conn, want, position="A", title="Be Brave", bpm=128.0, camelot_key="9B")
    tags.add(conn, "record", house, "French")
    tags.add(conn, "track", h1, "peak")
    tags.add(conn, "record", techno, "peak")
    conn.close()
    return {"house": house, "techno": techno, "want": want, "h1": h1, "h2": h2, "t1": t1, "w1": w1}


def ids(resp):
    assert resp.status_code == 200, resp.text
    return [i["id"] for i in resp.json()["items"]]


def test_list_envelope_and_pagination(client, library):
    body = client.get("/api/records?limit=2").json()
    assert (body["total"], body["limit"], body["offset"], len(body["items"])) == (3, 2, 0, 2)
    assert body["items"][0]["track_count"] in (1, 2)
    rest = client.get("/api/records?limit=2&offset=2").json()
    assert len(rest["items"]) == 1
    assert client.get("/api/records?limit=0").status_code == 422


def test_list_items_summarise_bpm_range_and_keys(client, library):
    items = {i["id"]: i for i in client.get("/api/records").json()["items"]}
    house = items[library["house"]]
    assert (house["bpm_min"], house["bpm_max"], house["camelot_keys"]) == (123.0, 123.5, ["4A", "9A"])
    assert items[library["want"]]["camelot_keys"] == ["9B"]


def test_bpm_filter_reports_matching_tracks(client, library):
    resp = client.get("/api/records?bpm_min=123.2&bpm_max=124")
    assert ids(resp) == [library["house"]]
    assert resp.json()["items"][0]["matched_track_ids"] == [library["h2"]]
    assert client.get("/api/records").json()["items"][0]["matched_track_ids"] is None


def test_key_filter_accepts_musical_and_camelot(client, library):
    expected = {library["house"], library["techno"]}
    for key in ("4A", "F minor", "Fm"):
        assert set(ids(client.get("/api/records", params={"key": key}))) == expected
    assert client.get("/api/records?key=nonsense").status_code == 422


def test_bpm_and_key_must_match_on_the_same_track(client, library):
    # house has 123 BPM in 4A (h1) and 9A at 123.5 (h2): 4A + 123.4..124 matches no single track
    assert ids(client.get("/api/records?key=4A&bpm_min=123.4&bpm_max=124")) == []
    both = client.get("/api/records?key=4A&bpm_min=122&bpm_max=124").json()["items"]
    assert [(r["id"], r["matched_track_ids"]) for r in both] == [(library["house"], [library["h1"]])]


def test_tag_filter_covers_record_and_track_tags_and_is_anded(client, library):
    assert set(ids(client.get("/api/records?tag=peak"))) == {library["house"], library["techno"]}
    assert ids(client.get("/api/records?tag=peak&tag=french")) == [library["house"]]
    assert ids(client.get("/api/records?tag=nope")) == []


def test_status_and_text_filters(client, library):
    assert ids(client.get("/api/records?status=wantlist")) == [library["want"]]
    assert ids(client.get("/api/records?q=daft")) == [library["house"]]
    assert ids(client.get("/api/records?q=dis")) == [library["house"]]  # prefix match
    assert ids(client.get('/api/records?q="; DROP TABLE')) == []  # punctuation cannot break FTS
    client.post("/api/notes", json={"type": "location", "body": "second shelf", "record_id": library["techno"]})
    client.post("/api/notes", json={"type": "cue-points", "body": "drop at 1:04", "track_id": library["w1"]})
    assert ids(client.get("/api/records?q=shelf")) == [library["techno"]]
    assert ids(client.get("/api/records?q=drop")) == [library["want"]]  # via a track note


def test_combined_filters(client, library):
    resp = client.get("/api/records?key=4A&tag=peak&status=owned&bpm_min=130")
    assert ids(resp) == [library["techno"]]


def test_get_patch_delete_record(client, library):
    rid = library["house"]
    detail = client.get(f"/api/records/{rid}").json()
    assert detail["tags"] == ["french"] and len(detail["tracks"]) == 2
    assert detail["tracks"][0]["tags"] == ["peak"]
    patched = client.patch(f"/api/records/{rid}", json={"label": "Parlophone", "year": 2002})
    assert patched.json()["label"] == "Parlophone" and patched.json()["year"] == 2002
    assert client.patch(f"/api/records/{rid}", json={"artist": None}).status_code == 422
    assert client.patch(f"/api/records/{rid}", json={"status": "bogus"}).status_code == 422
    assert client.get("/api/records/999").status_code == 404
    assert client.delete(f"/api/records/{rid}").status_code == 204
    assert client.get(f"/api/records/{rid}").status_code == 404
    assert client.delete(f"/api/records/{rid}").status_code == 404


def test_status_change_to_owned_queues_discogs_sync(client, library, db_path):
    client.patch(f"/api/records/{library['want']}", json={"status": "owned"})
    conn = connect(db_path)
    queued = jobs.list_by_status(conn, "queued")
    assert [(j["type"], j["record_id"]) for j in queued] == [("discogs_sync", library["want"])]
    conn.close()
    client.patch(f"/api/records/{library['want']}", json={"year": 1994})  # no status change: no new job
    conn = connect(db_path)
    assert len(jobs.list_by_status(conn, "queued")) == 1
    conn.close()


def test_error_format(client, library):
    missing = client.get("/api/records/999")
    assert missing.json() == {"error": {"code": "not_found", "message": "record not found"}}
    invalid = client.get("/api/records?limit=abc").json()["error"]
    assert invalid["code"] == "validation_error" and invalid["details"][0]["field"] == "limit"


def test_track_search_endpoint(client, library):
    resp = client.get("/api/tracks?bpm_min=120&bpm_max=130&key=Am")
    assert resp.json()["total"] == 0
    resp = client.get("/api/tracks?key=F minor")
    hits = resp.json()["items"]
    assert {h["id"] for h in hits} == {library["h1"], library["t1"]}
    assert {h["record"]["artist"] for h in hits} == {"Daft Punk", "Jeff Mills"}
    # tag inherited from the record, and a track's own tag
    assert {h["id"] for h in client.get("/api/tracks?tag=peak").json()["items"]} == {
        library["h1"], library["t1"]}
    assert [h["id"] for h in client.get("/api/tracks?q=aero").json()["items"]] == [library["h2"]]
    assert [h["id"] for h in client.get("/api/tracks?status=wantlist").json()["items"]] == [library["w1"]]
    assert client.get(f"/api/tracks/{library['h1']}").json()["title"] == "One More Time"
    assert client.get("/api/tracks/999").status_code == 404
