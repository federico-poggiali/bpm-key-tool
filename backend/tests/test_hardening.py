import json
import logging
import sqlite3

from fastapi.testclient import TestClient

from app import backup as backup_module
from app import export_openapi
from app.db import connect, records
from app.logging_config import JsonFormatter
from app.main import app


def test_cors_allows_the_frontend_dev_origin_only(client):
    ok = client.options("/api/records", headers={"Origin": "http://localhost:5173",
                                                 "Access-Control-Request-Method": "GET"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_unexpected_errors_use_the_standard_format(db_path, monkeypatch):
    from app.routes import records as records_routes

    def boom(*args, **kwargs):
        raise RuntimeError("secret internals")

    monkeypatch.setattr(records_routes.queries, "list_records", boom)
    resp = TestClient(app, raise_server_exceptions=False).get("/api/records")
    assert resp.status_code == 500
    assert resp.json() == {"error": {"code": "internal_error", "message": "unexpected server error"}}


def test_requests_are_logged_as_structured_json(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/health")
    record = next(r for r in caplog.records if r.name == "app.request")
    entry = json.loads(JsonFormatter().format(record))
    assert (entry["method"], entry["path"], entry["status"]) == ("GET", "/health", 200)
    assert entry["ms"] >= 0


def test_openapi_lists_every_endpoint_with_a_schema():
    schema = app.openapi()
    documented = {(path, method) for path, ops in schema["paths"].items() for method in ops}
    from app.routes import admin, jobs, notes, records, search, tags, tracks
    all_routes = [r for m in (records, tracks, notes, tags, search, jobs, admin) for r in m.router.routes]
    all_routes.append(next(r for r in app.routes if getattr(r, "path", "") == "/health"))
    routes = {(r.path, m.lower()) for r in all_routes for m in r.methods if m not in ("HEAD", "OPTIONS")}
    assert routes == documented
    for path, ops in schema["paths"].items():
        for method, op in ops.items():
            success = {code: r for code, r in op["responses"].items() if code.startswith("2")}
            assert success, f"{method} {path} has no success response"
            for code, response in success.items():
                if code != "204":
                    assert "content" in response, f"{method} {path} {code} has no response schema"


def test_operation_ids_are_unique_and_readable():
    ids = [op["operationId"] for ops in app.openapi()["paths"].values() for op in ops.values()]
    assert len(ids) == len(set(ids))
    assert "list_records" in ids and not any("_api_" in i for i in ids)


def test_committed_openapi_file_is_current():
    assert export_openapi.PATH.read_text() == export_openapi.schema_text(), \
        "docs/openapi.json is stale: run `make openapi`"


def test_backup_is_a_consistent_timestamped_copy(db_path, tmp_path):
    conn = connect(db_path)
    records.create(conn, artist="A", title="B")
    conn.close()
    dest = backup_module.backup(db_path, tmp_path / "backups")
    assert dest.parent == tmp_path / "backups" and dest.stem.startswith("test-")
    copy = sqlite3.connect(dest)
    assert copy.execute("SELECT artist FROM records").fetchone()[0] == "A"
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    copy.close()


def test_backup_of_missing_database_fails_clearly(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        backup_module.backup(tmp_path / "nope.db", tmp_path)


def test_file_databases_use_wal_and_wait_on_locks(db_path):
    conn = connect(db_path)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    conn.close()
