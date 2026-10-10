import json
import math
import struct
import wave
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import config
from app.db import connect, migrate
from app.deps import get_discogs, get_embedder, require_embedder
from app.discogs import DiscogsClient
from app.embeddings.provider import FakeProvider
from app.jobs.runner import JobRunner
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def fake_discogs_transport(calls: list[str] | None = None,
                           collection: dict[int, list[int]] | None = None,
                           fail_collection: bool = False) -> httpx.MockTransport:
    """Serves saved real responses. Master 137924 resolves to release 12472 (served as 'cd')."""
    releases = {
        9261843: load_fixture("release_simple.json"),
        46673: load_fixture("release_heading.json"),
        12472: {**load_fixture("release_cd.json"), "id": 12472},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        parts = request.url.path.strip("/").split("/")
        if request.url.path == "/oauth/identity":
            return httpx.Response(200, json={"username": "tester"})
        if parts[:3] == ["users", "tester", "collection"]:
            if fail_collection:
                return httpx.Response(500)
            owned = collection if collection is not None else {}
            if parts[3] == "releases":  # GET instances of one release
                rid = int(parts[4])
                instances = [{"instance_id": i} for i in owned.get(rid, [])]
                return httpx.Response(200, json={"releases": instances})
            rid = int(parts[6])
            if request.method == "POST":
                instance = 1000 + sum(len(v) for v in owned.values())
                owned.setdefault(rid, []).append(instance)
                return httpx.Response(201, json={"instance_id": instance})
            if request.method == "DELETE":
                owned[rid].remove(int(parts[8]))
                return httpx.Response(204)
        if parts[0] == "releases" and int(parts[1]) in releases:
            return httpx.Response(200, json=releases[int(parts[1])])
        if parts[0] == "masters" and int(parts[1]) == 137924:
            return httpx.Response(200, json=load_fixture("master_137924.json"))
        return httpx.Response(404, json={"message": "not found"})

    return httpx.MockTransport(handler)


def make_wav(path: Path, bpm: float = 120, freqs=(220.0, 261.63, 329.63), seconds: float = 20) -> Path:
    """A click track over a sustained chord (A minor by default)."""
    rate = 44100
    beat = int(rate * 60 / bpm)
    frames = bytearray()
    for i in range(int(rate * seconds)):
        tone = sum(math.sin(2 * math.pi * f * i / rate) for f in freqs) / len(freqs) * 0.3
        pos = i % beat
        click = math.exp(-pos / 200) * math.sin(2 * math.pi * 1000 * pos / rate) * 0.6 if pos < 2000 else 0
        frames += struct.pack("<h", int(max(-1, min(1, tone + click)) * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return path


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", path)
    conn = connect(path)
    migrate(conn)
    conn.close()
    return path


@pytest.fixture
def audio_dir(tmp_path, monkeypatch):
    path = tmp_path / "audio"
    path.mkdir()
    monkeypatch.setattr(config, "AUDIO_DIR", path)
    return path


@pytest.fixture
def discogs_calls():
    return []


@pytest.fixture
def collection():
    return {}


def make_discogs(calls=None, collection=None, fail_collection=False) -> DiscogsClient:
    transport = fake_discogs_transport(calls, collection, fail_collection)
    return DiscogsClient("test-token", client=httpx.Client(transport=transport), sleep=lambda s: None)


@pytest.fixture
def client(db_path, audio_dir, discogs_calls, collection):
    app.dependency_overrides[get_discogs] = lambda: make_discogs(discogs_calls, collection)
    fake = FakeProvider()
    app.dependency_overrides[get_embedder] = lambda: fake
    app.dependency_overrides[require_embedder] = lambda: fake
    app.state.runner = JobRunner({})
    yield TestClient(app)
    app.dependency_overrides.clear()
