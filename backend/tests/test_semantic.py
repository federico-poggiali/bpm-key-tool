import pytest

from app.db import connect, notes, records, tracks
from app.embeddings import service
from app.embeddings.provider import DIMENSIONS, EmbeddingError, FakeProvider, OpenAIProvider


@pytest.fixture
def rec(db_path):
    conn = connect(db_path)
    rid = records.create(conn, artist="A", title="B")
    t1 = tracks.create(conn, rid, position="A1", title="First")
    conn.close()
    return rid, t1


def embedded(db_path, note_id):
    conn = connect(db_path)
    try:
        return notes.has_embedding(conn, note_id)
    finally:
        conn.close()


def test_prose_is_embedded_on_save_but_other_types_are_not(client, rec, db_path):
    rid, _ = rec
    prose = client.post("/api/notes", json={"type": "prose", "body": "huge energy", "record_id": rid}).json()
    other = client.post("/api/notes", json={"type": "location", "body": "shelf", "record_id": rid}).json()
    assert embedded(db_path, prose["id"]) and not embedded(db_path, other["id"])


def test_reembed_on_edit_and_cleanup_on_type_change_and_delete(client, rec, db_path):
    rid, _ = rec
    nid = client.post("/api/notes", json={"type": "prose", "body": "slow burner", "record_id": rid}).json()["id"]
    conn = connect(db_path)
    before = conn.execute("SELECT embedding FROM note_embeddings WHERE note_id = ?", (nid,)).fetchone()[0]
    conn.close()
    client.patch(f"/api/notes/{nid}", json={"body": "absolute banger"})
    conn = connect(db_path)
    after = conn.execute("SELECT embedding FROM note_embeddings WHERE note_id = ?", (nid,)).fetchone()[0]
    conn.close()
    assert before != after  # re-embedded with the new text

    client.patch(f"/api/notes/{nid}", json={"type": "condition"})
    assert not embedded(db_path, nid)
    client.patch(f"/api/notes/{nid}", json={"type": "prose"})
    assert embedded(db_path, nid)
    client.delete(f"/api/notes/{nid}")
    assert not embedded(db_path, nid)


def test_embeddings_are_removed_when_a_record_or_track_is_deleted(client, rec, db_path):
    rid, t1 = rec
    client.post("/api/notes", json={"type": "prose", "body": "on record", "record_id": rid})
    client.post("/api/notes", json={"type": "prose", "body": "on track", "track_id": t1})
    conn = connect(db_path)
    assert conn.execute("SELECT count(*) FROM note_embeddings").fetchone()[0] == 2
    conn.close()
    client.delete(f"/api/records/{rid}")
    conn = connect(db_path)
    assert conn.execute("SELECT count(*) FROM note_embeddings").fetchone()[0] == 0
    conn.close()


def test_semantic_search_ranks_by_similarity_and_returns_parents(client, rec):
    rid, t1 = rec
    client.post("/api/notes", json={"type": "prose", "body": "huge energy and the floor erupted", "track_id": t1})
    client.post("/api/notes", json={"type": "prose", "body": "quiet ambient closing track", "record_id": rid})
    client.post("/api/notes", json={"type": "location", "body": "energy shelf", "record_id": rid})  # not prose
    hits = client.get("/api/search/semantic", params={"q": "floor erupted energy"}).json()
    assert [h["note"]["body"] for h in hits][0] == "huge energy and the floor erupted"
    assert len(hits) == 2  # the location note is not searchable by meaning
    assert hits[0]["score"] > hits[1]["score"]
    assert hits[0]["track"]["id"] == t1 and hits[0]["record"]["id"] == rid
    assert hits[1]["track"] is None
    assert len(client.get("/api/search/semantic", params={"q": "energy", "limit": 1}).json()) == 1
    assert client.get("/api/search/semantic").status_code == 422


def test_admin_reembed_rebuilds_everything(client, rec, db_path):
    rid, _ = rec
    nid = client.post("/api/notes", json={"type": "prose", "body": "x y z", "record_id": rid}).json()["id"]
    conn = connect(db_path)
    conn.execute("DELETE FROM note_embeddings")
    conn.commit()
    conn.close()
    assert not embedded(db_path, nid)
    assert client.post("/api/admin/reembed").json() == {"embedded": 1}
    assert embedded(db_path, nid)


def test_no_openai_key_means_notes_save_but_search_is_unavailable(db_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import config
    from app.main import app
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    client = TestClient(app)
    conn = connect(db_path)
    rid = records.create(conn, artist="A", title="B")
    conn.close()
    note = client.post("/api/notes", json={"type": "prose", "body": "kept", "record_id": rid})
    assert note.status_code == 201 and not embedded(db_path, note.json()["id"])
    resp = client.get("/api/search/semantic", params={"q": "kept"})
    assert resp.status_code == 503 and "OPENAI_API_KEY" in resp.json()["error"]["message"]


def test_provider_failure_does_not_lose_the_note(db_path, rec):
    class Broken:
        def embed(self, texts):
            raise EmbeddingError("down")

    rid, _ = rec
    conn = connect(db_path)
    nid = notes.create(conn, type="prose", body="still here", record_id=rid)
    service.sync_note(conn, Broken(), nid)
    assert notes.get(conn, nid)["body"] == "still here" and not notes.has_embedding(conn, nid)
    conn.close()


def test_fake_provider_is_deterministic_and_unit_length():
    a, b = FakeProvider().embed(["banging track", "banging track"])
    assert a == b and len(a) == DIMENSIONS
    assert abs(sum(v * v for v in a) - 1.0) < 1e-9


def test_openai_provider_request_shape():
    import httpx
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.read()
        return httpx.Response(200, json={"data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]})

    provider = OpenAIProvider("sk-test", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert provider.embed(["a", "b"]) == [[1.0], [2.0]]  # restored to input order
    assert seen["auth"] == "Bearer sk-test" and b"text-embedding-3-small" in seen["body"]
    with pytest.raises(EmbeddingError):
        OpenAIProvider("")
