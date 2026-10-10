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


def test_intake_enqueues_both_jobs_for_owned(client):
    body = client.post("/api/records/intake", json=INTAKE).json()
    assert set(body["jobs"]) == {"analysis", "discogs_sync"}
    assert job_of(client, body["jobs"]["analysis"])["type"] == "analysis"
    assert job_of(client, body["jobs"]["discogs_sync"])["type"] == "discogs_sync"


def test_wantlist_is_not_synced_and_duplicates_enqueue_nothing(client):
    body = client.post("/api/records/intake", json={**INTAKE, "status": "wantlist"}).json()
    assert body["jobs"]["discogs_sync"] is None and body["jobs"]["analysis"]
    again = client.post("/api/records/intake", json={**INTAKE, "status": "wantlist"}).json()
    assert again["jobs"] is None
    assert client.post(f"/api/records/{body['id']}/sync-discogs").status_code == 400


def test_sync_adds_once_and_marks_record(client, collection, db_path):
    body = client.post("/api/records/intake", json=INTAKE).json()
    rid = body["id"]
    client.app.state.runner = runner = runner_with(collection)
    runner.run_pending()  # the sync job intake queued (its analysis job has no handler here)
    job = job_of(client, body["jobs"]["discogs_sync"])
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
    body = client.post("/api/records/intake", json=INTAKE).json()
    rid = body["id"]
    client.app.state.runner = failing = runner_with(collection, fail=True)
    failing.run_pending()
    job = job_of(client, body["jobs"]["discogs_sync"])
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
    body = client.post("/api/records/intake", json=INTAKE).json()
    client.app.state.runner = runner = JobRunner({
        sync.JOB_TYPE: sync.make_handler(lambda: make_discogs(fail_collection=True)),
        "analysis": lambda conn, job: {"ok": True},
    })
    runner.run_pending()
    assert job_of(client, body["jobs"]["discogs_sync"])["status"] == "failed"
    assert job_of(client, body["jobs"]["analysis"])["status"] == "done"
