import subprocess

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import vault as vault_module
from app.db import connect, notes, records, tracks
from app.main import mount_frontend


def make_record(db_path, release_id=9261843):
    conn = connect(db_path)
    rid = records.create(conn, artist="A", title="B", discogs_release_id=release_id)
    t1 = tracks.create(conn, rid, position="A1", title="First")
    t2 = tracks.create(conn, rid, position="A2", title="Second")
    conn.close()
    return rid, t1, t2


def test_assign_audio_file_by_hand_and_it_survives_matching(client, db_path, audio_dir):
    rid, t1, t2 = make_record(db_path)
    folder = audio_dir / "9261843"
    folder.mkdir()
    (folder / "odd name.wav").write_bytes(b"x")
    (folder / "A2 - Second.wav").write_bytes(b"x")

    before = client.get(f"/api/records/{rid}/audio-match").json()
    assert [u["file"] for u in before["unmatched_files"]] == ["odd name.wav"]

    resp = client.post(f"/api/tracks/{t1}/audio", json={"file": "odd name.wav"})
    assert resp.status_code == 200 and resp.json()["audio_path"].endswith("odd name.wav")
    after = client.get(f"/api/records/{rid}/audio-match").json()
    assert {(m["track_id"], m["method"]) for m in after["matched"]} == {(t1, "assigned"), (t2, "position")}
    assert after["unmatched_files"] == [] and after["unmatched_tracks"] == []

    # one file, one track: moving it clears the previous owner
    client.post(f"/api/tracks/{t2}/audio", json={"file": "odd name.wav"})
    assert client.get(f"/api/tracks/{t1}").json()["audio_path"] is None
    assert client.delete(f"/api/tracks/{t2}/audio").json()["audio_path"] is None


def test_assign_audio_rejects_bad_input(client, db_path, audio_dir):
    _, t1, _ = make_record(db_path)
    (audio_dir / "9261843").mkdir()
    assert client.post(f"/api/tracks/{t1}/audio", json={"file": "missing.wav"}).status_code == 404
    assert client.post(f"/api/tracks/{t1}/audio", json={"file": "../secret.wav"}).status_code == 422
    assert client.post("/api/tracks/999/audio", json={"file": "x.wav"}).status_code == 404
    assert client.delete("/api/tracks/999/audio").status_code == 404


def test_exact_search_returns_snippets_and_records(client, db_path):
    rid, t1, _ = make_record(db_path)
    conn = connect(db_path)
    notes.create(conn, type="prose", body="Huge energy, the floor erupted at midnight", track_id=t1)
    notes.create(conn, type="location", body="second shelf", record_id=rid)
    conn.close()
    body = client.get("/api/search/exact", params={"q": "erupted"}).json()
    assert len(body["notes"]) == 1
    hit = body["notes"][0]
    assert "\x02erupted\x03" in hit["snippet"]
    assert hit["track"]["id"] == t1 and hit["record"]["id"] == rid
    assert client.get("/api/search/exact", params={"q": "a"}).json()["records"][0]["id"] == rid
    assert client.get("/api/search/exact", params={"q": "!!!"}).json() == {"notes": [], "records": []}
    assert client.get("/api/search/exact").status_code == 422


def test_open_vault_reveals_the_examples_file(client, tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "VAULT_DIR", tmp_path)
    assert client.post("/api/admin/open-vault").json()["opened"] is False  # nothing generated yet
    (tmp_path / vault_module.EXAMPLES_FILE).write_text("x")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a[0]))
    monkeypatch.setattr("sys.platform", "darwin")
    body = client.post("/api/admin/open-vault").json()
    assert body["opened"] and calls == [["open", "-R", body["path"]]]


def test_built_frontend_is_served_with_client_side_routes(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (dist / "favicon.svg").write_text("<svg/>")
    app = FastAPI()
    assert mount_frontend(app, tmp_path / "nope") is False
    assert mount_frontend(app, dist) is True
    client = TestClient(app)
    assert client.get("/records/5").text == "<html>app</html>"  # SPA route falls back to index
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/favicon.svg").text == "<svg/>"
    assert client.get("/api/unknown").status_code == 404
    assert client.get("/../../etc/passwd").text == "<html>app</html>"  # never escapes dist
