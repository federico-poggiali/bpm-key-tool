from app import sync
from app.db import connect, records
from app.jobs.runner import JobRunner
from tests.conftest import make_discogs

INTAKE = {"discogs_url": "https://www.discogs.com/release/9261843"}


def runner_with(collection=None, fail=False):
    return JobRunner({sync.JOB_TYPE: sync.make_handler(
        lambda: make_discogs(collection=collection, fail_collection=fail))})


def job_of(client, job_id):
    return client.get(f"/api/jobs/{job_id}").json()


def test_intake_starts_no_jobs_so_the_user_chooses(client):
    body = client.post("/api/records/intake", json=INTAKE).json()
    assert body["jobs"] is None
    again = client.post("/api/records/intake", json=INTAKE).json()
    assert again["jobs"] is None


def test_wantlist_is_not_synced(client):
    rid = client.post("/api/records/intake", json={**INTAKE, "status": "wantlist"}).json()["id"]
    assert client.post(f"/api/records/{rid}/sync-discogs").status_code == 400


def test_sync_adds_once_and_marks_record(client, collection, db_path):
    rid = client.post("/api/records/intake", json=INTAKE).json()["id"]
    client.app.state.runner = runner = runner_with(collection)
    first = client.post(f"/api/records/{rid}/sync-discogs").json()["job_id"]
    runner.run_pending()
    job = job_of(client, first)
    assert job["status"] == "done" and job["result"]["added"] is True
    assert len(collection[9261843]) == 1
    conn = connect(db_path)
    assert records.get(conn, rid)["discogs_collection_synced"] == 1
    conn.close()
    # Retrying never creates a second copy: Discogs is asked first.
    retry = client.post(f"/api/records/{rid}/sync-discogs").json()["job_id"]
    runner.run_pending()
    assert job_of(client, retry)["result"]["added"] is False
    assert len(collection[9261843]) == 1


def test_release_already_in_collection_is_not_added_again(client, db_path):
    owned = {9261843: [42]}
    rid = client.post("/api/records/intake", json=INTAKE).json()["id"]
    client.app.state.runner = runner = runner_with(owned)
    job_id = client.post(f"/api/records/{rid}/sync-discogs").json()["job_id"]
    runner.run_pending()
    assert job_of(client, job_id)["result"] == {"instance_id": 42, "added": False}
    assert owned == {9261843: [42]}


def test_sync_failure_is_stored_and_retryable(client, collection, db_path):
    rid = client.post("/api/records/intake", json=INTAKE).json()["id"]
    client.app.state.runner = failing = runner_with(collection, fail=True)
    first = client.post(f"/api/records/{rid}/sync-discogs").json()["job_id"]
    failing.run_pending()
    job = job_of(client, first)
    assert job["status"] == "failed" and "500" in job["error"]
    conn = connect(db_path)
    assert records.get(conn, rid)["discogs_collection_synced"] == 0
    conn.close()
    client.app.state.runner = working = runner_with(collection)
    retry = client.post(f"/api/records/{rid}/sync-discogs").json()["job_id"]
    working.run_pending()
    assert job_of(client, retry)["status"] == "done"
    assert len(collection[9261843]) == 1


def test_sync_failure_does_not_touch_analysis_job(client, collection, db_path):
    rid = client.post("/api/records/intake", json=INTAKE).json()["id"]
    client.app.state.runner = runner = JobRunner({
        sync.JOB_TYPE: sync.make_handler(lambda: make_discogs(fail_collection=True)),
        "analysis": lambda conn, job: {"ok": True},
    })
    sync_job = client.post(f"/api/records/{rid}/sync-discogs").json()["job_id"]
    analysis_job = client.post(f"/api/records/{rid}/analyze").json()["job_id"]
    runner.run_pending()
    assert job_of(client, sync_job)["status"] == "failed"
    assert job_of(client, analysis_job)["status"] == "done"


def test_analyze_can_be_limited_to_chosen_tracks(client):
    rec = client.post("/api/records/intake", json=INTAKE).json()
    ids = [t["id"] for t in rec["tracks"]]
    seen = []
    client.app.state.runner = runner = JobRunner({"analysis": lambda conn, job: seen.append(job["params"]) or {}})
    job = client.post(f"/api/records/{rec['id']}/analyze", json={"track_ids": ids[:1]}).json()["job_id"]
    whole = client.post(f"/api/records/{rec['id']}/analyze").json()["job_id"]
    runner.run_pending()
    assert seen == [{"track_ids": ids[:1]}, None]
    assert job_of(client, job)["status"] == job_of(client, whole)["status"] == "done"
    assert client.post(f"/api/records/{rec['id']}/analyze", json={"track_ids": [999999]}).status_code == 400
    assert client.post(f"/api/records/{rec['id']}/analyze", json={"track_ids": []}).status_code == 400
