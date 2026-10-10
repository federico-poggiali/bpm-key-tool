import re

from app.analysis import engine
from app.analysis.job import make_handler
from app.db import connect, records, tracks
from app.jobs.runner import JobRunner
from tests.conftest import make_wav


def setup_record(db_path, audio_dir, release_id=555):
    conn = connect(db_path)
    rid = records.create(conn, artist="A", title="B", discogs_release_id=release_id)
    t1 = tracks.create(conn, rid, position="A1", title="First")
    t2 = tracks.create(conn, rid, position="A2", title="Second")
    conn.close()
    folder = audio_dir / str(release_id)
    folder.mkdir()
    return rid, t1, t2, folder


def fake_analyze(path):
    return {"bpm": 124.0, "key": "A minor", "camelot_key": "8A", "confidence": 0.7,
            "raw": {"bpm_alt": 62.0}}


def test_alternate_bpm():
    assert engine.alternate_bpm(128) == 64
    assert engine.alternate_bpm(80) == 160


def test_analysis_job_fills_matched_tracks_and_reports_mismatches(client, db_path, audio_dir):
    rid, t1, t2, folder = setup_record(db_path, audio_dir)
    (folder / "A1 - First.wav").write_bytes(b"x")
    (folder / "mystery.wav").write_bytes(b"x")
    runner = JobRunner({"analysis": make_handler(fake_analyze)})
    client.app.state.runner = runner

    resp = client.post(f"/api/records/{rid}/analyze")
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "queued"
    runner.run_pending()

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "done"
    assert [f["file"] for f in job["result"]["unmatched_files"]] == ["mystery.wav"]
    assert [t["track_id"] for t in job["result"]["unmatched_tracks"]] == [t2]
    conn = connect(db_path)
    first, second = tracks.get(conn, t1), tracks.get(conn, t2)
    assert (first["bpm"], first["camelot_key"], first["confidence"]) == (124.0, "8A", 0.7)
    assert first["analysis_raw"] == {"bpm_alt": 62.0} and first["analyzed_at"]
    assert second["bpm"] is None
    conn.close()


def test_job_fails_cleanly_without_audio(client, db_path, audio_dir):
    rid, *_ = setup_record(db_path, audio_dir)
    runner = JobRunner({"analysis": make_handler(fake_analyze)})
    client.app.state.runner = runner
    job_id = client.post(f"/api/records/{rid}/analyze").json()["job_id"]
    runner.run_pending()
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "failed" and "no audio files" in job["error"]


def test_one_bad_file_does_not_block_the_others(client, db_path, audio_dir):
    rid, t1, t2, folder = setup_record(db_path, audio_dir)
    (folder / "A1.wav").write_bytes(b"x")
    (folder / "A2.wav").write_bytes(b"x")

    def flaky(path):
        if path.name == "A1.wav":
            raise RuntimeError("corrupt")
        return fake_analyze(path)

    runner = JobRunner({"analysis": make_handler(flaky)})
    client.app.state.runner = runner
    job_id = client.post(f"/api/records/{rid}/analyze").json()["job_id"]
    runner.run_pending()
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "done"
    assert job["result"]["errors"][0]["file"] == "A1.wav"
    assert job["result"]["analyzed_track_ids"] == [t2]


def test_analyze_endpoint_errors(client, db_path):
    assert client.post("/api/records/99/analyze").status_code == 404
    conn = connect(db_path)
    rid = records.create(conn, artist="A", title="B")
    conn.close()
    assert client.post(f"/api/records/{rid}/analyze").status_code == 400
    assert client.get("/api/jobs/99").status_code == 404


def test_audio_match_endpoint(client, db_path, audio_dir):
    rid, t1, t2, folder = setup_record(db_path, audio_dir)
    (folder / "A2 - Second.wav").write_bytes(b"x")
    report = client.get(f"/api/records/{rid}/audio-match").json()
    assert [m["track_id"] for m in report["matched"]] == [t2]
    assert [t["track_id"] for t in report["unmatched_tracks"]] == [t1]


def test_real_engine_on_short_audio(client, db_path, audio_dir):
    """End to end with bpmkey/Essentia on synthetic clips (checks wiring, not accuracy)."""
    rid, t1, t2, folder = setup_record(db_path, audio_dir)
    make_wav(folder / "A1 - First.wav", bpm=120)
    make_wav(folder / "A2 - Second.wav", bpm=100, freqs=(196.0, 246.94, 293.66))
    make_wav(folder / "stray.wav", bpm=90)
    runner = JobRunner({"analysis": make_handler()})
    client.app.state.runner = runner
    job_id = client.post(f"/api/records/{rid}/analyze").json()["job_id"]
    runner.run_pending()
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "done", job
    assert [f["file"] for f in job["result"]["unmatched_files"]] == ["stray.wav"]
    conn = connect(db_path)
    for tid in (t1, t2):
        t = tracks.get(conn, tid)
        assert t["bpm"] and 70 <= t["bpm"] <= 180
        assert re.fullmatch(r"(1[0-2]|[1-9])[AB]", t["camelot_key"])
        assert 0 <= t["confidence"] <= 1
        assert t["analysis_raw"]["bpm_alt"] and t["audio_path"]
    conn.close()


def test_restart_recovery(db_path):
    from app.db import jobs
    conn = connect(db_path)
    stuck = jobs.create(conn, "analysis")
    jobs.set_status(conn, stuck, "running")
    conn.close()
    runner = JobRunner({})
    runner.start()
    runner.stop()
    conn = connect(db_path)
    assert jobs.get(conn, stuck)["status"] == "failed"
    conn.close()
