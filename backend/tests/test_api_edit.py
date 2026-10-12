import pytest

from app.analysis.job import make_handler
from app.db import connect, records, tracks
from app.jobs.runner import JobRunner
from tests.conftest import make_discogs


@pytest.fixture
def rec(db_path):
    conn = connect(db_path)
    rid = records.create(conn, artist="A", title="B", discogs_release_id=9261843)
    t1 = tracks.create(conn, rid, position="A1", title="First")
    t2 = tracks.create(conn, rid, position="A2", title="Second")
    conn.close()
    return rid, t1, t2


def test_manual_override_survives_validation_unless_overwritten(client, rec, db_path):
    rid, t1, _ = rec
    resp = client.patch(f"/api/tracks/{t1}", json={"bpm": 126.5, "key": "F# minor"})
    body = resp.json()
    assert (body["bpm"], body["key"], body["camelot_key"]) == (126.5, "F# minor", "11A")
    assert body["bpm_manual"] and body["key_manual"]

    lookup = {"bpm": 100.0, "key": "C major", "camelot_key": "8B", "confidence": 0.9, "raw": {"x": 1}}
    runner = JobRunner({"analysis": make_handler(make_discogs, lookup_fn=lambda *a: {t1: lookup})})
    client.app.state.runner = runner

    def analyse_and_validate(**extra):
        client.post(f"/api/records/{rid}/analyze")
        runner.run_pending()
        assert client.post(f"/api/records/{rid}/validate", json={"track_ids": [t1], **extra}).status_code == 200
        return client.get(f"/api/tracks/{t1}").json()

    after = analyse_and_validate()
    assert (after["bpm"], after["camelot_key"]) == (126.5, "11A")  # untouched
    assert after["analysis_raw"] == {"x": 1}  # the analysis itself is still recorded

    # Unlock BPM only: validation may overwrite BPM but not the key.
    assert not client.patch(f"/api/tracks/{t1}", json={"unlock": ["bpm"]}).json()["bpm_manual"]
    after = analyse_and_validate()
    assert (after["bpm"], after["camelot_key"], after["key_manual"]) == (100.0, "11A", True)

    # Told to overwrite: the hand-entered key is replaced and its lock released.
    after = analyse_and_validate(overwrite_manual=True)
    assert (after["camelot_key"], after["confidence"], after["key_manual"]) == ("8B", 0.9, False)


def test_manual_key_accepts_camelot_and_rejects_nonsense(client, rec):
    _, t1, _ = rec
    assert client.patch(f"/api/tracks/{t1}", json={"key": "8B"}).json()["key"] == "C major"
    assert client.patch(f"/api/tracks/{t1}", json={"key": "H#"}).status_code == 422
    assert client.patch(f"/api/tracks/{t1}", json={"bpm": -5}).status_code == 422
    assert client.patch(f"/api/tracks/{t1}", json={"bpm": 120, "unlock": ["bpm"]}).status_code == 422
    assert client.patch("/api/tracks/999", json={"bpm": 120}).status_code == 404


def test_notes_crud_record_and_track_level(client, rec):
    rid, t1, _ = rec
    rec_note = client.post("/api/notes", json={"type": "location", "body": "Shelf B", "record_id": rid})
    trk_note = client.post("/api/notes", json={"type": "prose", "body": "huge energy", "track_id": t1})
    assert rec_note.status_code == trk_note.status_code == 201
    detail = client.get(f"/api/records/{rid}").json()
    assert [n["body"] for n in detail["notes"]] == ["Shelf B"]
    assert [n["body"] for n in detail["tracks"][0]["notes"]] == ["huge energy"]

    nid = trk_note.json()["id"]
    assert client.patch(f"/api/notes/{nid}", json={"body": "floor erupted"}).json()["body"] == "floor erupted"
    assert client.patch(f"/api/notes/{nid}", json={"body": None}).status_code == 422
    assert client.delete(f"/api/notes/{nid}").status_code == 204
    assert client.delete(f"/api/notes/{nid}").status_code == 404
    assert client.patch("/api/notes/999", json={"body": "x"}).status_code == 404


def test_note_needs_exactly_one_existing_parent(client, rec):
    rid, t1, _ = rec
    bad = [{"type": "prose", "body": "x"},
           {"type": "prose", "body": "x", "record_id": rid, "track_id": t1},
           {"type": "", "body": "x", "record_id": rid}]
    assert [client.post("/api/notes", json=b).status_code for b in bad] == [422, 422, 422]
    assert client.post("/api/notes", json={"type": "a", "body": "x", "record_id": 999}).status_code == 404
    assert client.post("/api/notes", json={"type": "a", "body": "x", "track_id": 999}).status_code == 404


def test_tags_endpoints(client, rec):
    rid, t1, _ = rec
    assert client.post(f"/api/records/{rid}/tags", json={"name": "house"}).status_code == 404  # not designed yet
    gid = {g["name"]: g["id"] for g in client.get("/api/tag-groups").json()["items"]}
    for name, group in (("house", "Atmosphere"), ("peak", "Set role")):
        assert client.post(f"/api/tag-groups/{gid[group]}/tags", json={"name": name}).status_code == 201
    assert client.post(f"/api/records/{rid}/tags", json={"name": " House "}).json() == ["house"]
    assert client.post(f"/api/records/{rid}/tags", json={"name": "house"}).json() == ["house"]
    assert client.post(f"/api/tracks/{t1}/tags", json={"name": "House"}).json() == ["house"]
    assert client.post(f"/api/tracks/{t1}/tags", json={"name": "peak"}).json() == ["house", "peak"]
    counts = {t["name"]: t for t in client.get("/api/tags").json()["items"]}
    assert (counts["house"]["record_count"], counts["house"]["track_count"]) == (1, 1)
    assert client.delete(f"/api/tracks/{t1}/tags/peak").json() == ["house"]
    assert client.delete(f"/api/tracks/{t1}/tags/peak").status_code == 404
    assert client.delete(f"/api/records/{rid}/tags/HOUSE").json() == []
    assert client.post("/api/records/999/tags", json={"name": "x"}).status_code == 404
    assert client.post(f"/api/records/{rid}/tags", json={"name": ""}).status_code == 422


def test_tag_manager(client):
    groups = client.get("/api/tag-groups").json()["items"]
    assert [(g["name"], g["fixed"]) for g in groups] == [("Energy", True), ("Atmosphere", True), ("Set role", True)]
    energy = groups[0]["id"]
    assert client.patch(f"/api/tag-groups/{energy}", json={"name": "Vibe"}).status_code == 403
    assert client.delete(f"/api/tag-groups/{energy}").status_code == 403

    made = client.post("/api/tag-groups", json={"name": "Occasion"}).json()["items"]
    occasion = made[-1]["id"]
    assert client.post("/api/tag-groups", json={"name": "occasion"}).status_code == 422
    assert client.patch(f"/api/tag-groups/{occasion}", json={"name": "Venue"}).status_code == 200

    out = client.post(f"/api/tag-groups/{occasion}/tags", json={"name": " Warehouse "}).json()["items"]
    tag = out[-1]["tags"][0]
    assert tag["name"] == "warehouse"
    assert client.post(f"/api/tag-groups/{energy}/tags", json={"name": "warehouse"}).status_code == 422
    out = client.patch(f"/api/tag-defs/{tag['id']}", json={"group_id": energy, "name": "Peak"}).json()["items"]
    assert [t["name"] for t in out[0]["tags"]] == ["peak"] and out[-1]["tags"] == []
    assert client.patch("/api/tag-defs/999", json={"name": "x"}).status_code == 404

    assert client.delete(f"/api/tag-defs/{tag['id']}").status_code == 200
    assert client.delete(f"/api/tag-defs/{tag['id']}").status_code == 404
    assert client.delete(f"/api/tag-groups/{occasion}").status_code == 200
    assert client.delete(f"/api/tag-groups/{occasion}").status_code == 404
