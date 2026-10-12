import httpx
import pytest

from app.discogs import (
    DiscogsClient,
    DiscogsError,
    DiscogsNotFound,
    release_to_record,
    release_to_tracks,
)
from tests.conftest import fake_discogs_transport, load_fixture


def make_client(handler=None):
    transport = httpx.MockTransport(handler) if handler else fake_discogs_transport()
    sleeps: list[float] = []
    return DiscogsClient("t", client=httpx.Client(transport=transport), sleep=sleeps.append), sleeps


def test_resolve_release_and_master_urls():
    client, _ = make_client()
    assert client.resolve("https://www.discogs.com/release/9261843-Truncate-7-1") == (9261843, None)
    assert client.resolve("https://www.discogs.com/master/137924-Be-Brave") == (12472, 137924)
    with pytest.raises(DiscogsError, match="Not a Discogs"):
        client.resolve("https://example.com/nope")


def test_not_found():
    client, _ = make_client()
    with pytest.raises(DiscogsNotFound):
        client.release(1)


def test_retries_on_429_then_succeeds():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(429, headers={"Retry-After": "7"})
        return httpx.Response(200, json={"id": 5})

    client, sleeps = make_client(handler)
    assert client.release(5) == {"id": 5}
    assert sleeps == [7.0, 7.0]


def test_gives_up_after_retries():
    client, sleeps = make_client(lambda request: httpx.Response(429))
    with pytest.raises(DiscogsError, match="rate limit"):
        client.release(5)
    assert len(sleeps) == 5


def test_requires_token():
    with pytest.raises(DiscogsError):
        DiscogsClient("")


def test_record_mapping():
    record = release_to_record(load_fixture("release_cd.json"))
    assert record["artist"] == "Various"
    assert record["label"] == "Larvin Music Rights"
    assert record["year"] == 2018
    assert record["format"].startswith("2xVinyl, LP")
    assert record["cover_url"].startswith("http")


def test_tracks_side_positions_and_headings():
    positions = [t["position"] for t in release_to_tracks(load_fixture("release_cd.json"))]
    assert {"A1", "B1", "C1"} <= set(positions)
    # heading rows are skipped; only the two real tracks remain
    tracks = release_to_tracks(load_fixture("release_heading.json"))
    assert [(t["position"], t["duration_sec"]) for t in tracks] == [("A", 420), ("B", 333)]


def test_styles_are_imported_and_genres_are_not():
    record = release_to_record(load_fixture("release_simple.json"))
    assert record["styles"] == ["Acid", "Techno"]  # the release's genre ('Electronic') is not stored
    assert record["catno"] == "TRUNCATE14"
    assert release_to_record(load_fixture("release_heading.json"))["styles"] == ["UK Garage", "Techno"]


def test_genre_stands_in_only_when_a_release_has_no_styles():
    base = {k: v for k, v in load_fixture("release_simple.json").items() if k != "styles"}
    assert release_to_record({**base, "genres": ["Electronic"]})["styles"] == ["Electronic"]
    assert release_to_record({**base, "genres": []})["styles"] == []
    assert release_to_record({**base, "styles": [], "genres": ["Jazz"]})["styles"] == ["Jazz"]


def test_year_falls_back_to_the_released_date():
    base = {k: v for k, v in load_fixture("release_simple.json").items() if k not in ("year", "released")}
    assert release_to_record({**base, "year": 2018})["year"] == 2018
    assert release_to_record({**base, "year": 0, "released": "2011-05-01"})["year"] == 2011
    assert release_to_record({**base, "released": "1999"})["year"] == 1999
    assert release_to_record({**base, "released": "0000-00-00"})["year"] is None
    assert release_to_record(base)["year"] is None
