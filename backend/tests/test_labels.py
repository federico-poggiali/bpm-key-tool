import base64
import io

import pytest
from PIL import Image

from app.db import connect, notes, queries, records, tags, tracks
from app.labels import data as label_data
from app.labels import render as label_render
from app.labels.data import LabelData, LabelTrack


@pytest.fixture
def conn(db_path):
    c = connect(db_path)
    yield c
    c.close()


@pytest.fixture
def record_id(conn):
    rid = records.create(conn, artist="Jeff Mills (2)", title="The Bells", label="Purpose Maker",
                         catno="PM-01", year=1994, discogs_release_id=4242, styles=["Techno", "Minimal"])
    t1 = tracks.create(conn, rid, position="A", title="The Bells", bpm=135.04, key="F minor",
                       camelot_key="4A")
    tracks.create(conn, rid, position="B", title="Other", bpm=None, key="A minor")
    tags.create_tag(conn, 1, "peak")
    tags.add(conn, "track", t1, "peak")
    notes.create(conn, type="location", body="Shelf B", record_id=rid)
    notes.create(conn, type="prose", body="Relentless and hypnotic. Great after midnight.", record_id=rid)
    notes.create(conn, type="prose", body="Drop at two minutes", track_id=t1)
    return rid


def pixels(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png))


def sample(tracks_: list[LabelTrack] | None = None, **kw) -> LabelData:
    base = dict(artist="Jeff Mills", title="The Bells", label="Axis", catno="AX-1", year="1994",
                styles=["Techno"], note="A short note.", qr_url="https://www.discogs.com/release/1",
                tracks=tracks_ or [LabelTrack(position="A1", bpm="130", key="8A")])
    return LabelData(**{**base, **kw})


def warnings_of(data: LabelData) -> list[str]:
    return label_render.render(data)[1]


# ---- builder ----

def test_build_merges_record_tracks_tags_and_notes(conn, record_id):
    data = label_data.build(queries.record_detail(conn, record_id))
    assert data.artist == "Jeff Mills"  # the Discogs "(2)" is not for print
    assert (data.label, data.catno, data.year) == ("Purpose Maker", "PM-01", "1994")
    assert data.styles == ["Techno", "Minimal"]
    assert data.note == "Relentless and hypnotic."  # prose note, first sentence only
    assert data.qr_url == "https://www.discogs.com/release/4242"
    assert data.country is None  # not stored
    first, second = data.tracks
    assert (first.position, first.bpm, first.key, first.tags) == ("A", "135", "4A", ["peak"])
    assert first.note == "Drop at two minutes"
    assert (second.bpm, second.key, second.note) == (None, "A minor", None)  # falls back to the musical key


def test_clean_artist_only_drops_discogs_numbers():
    assert label_data.clean_artist("Aphex Twin") == "Aphex Twin"
    assert label_data.clean_artist("Jeff Mills (2) & DJ Rush (3)") == "Jeff Mills & DJ Rush"
    assert label_data.clean_artist("Blink (182)") == "Blink"
    assert label_data.clean_artist("(Not) A Number") == "(Not) A Number"


def test_a_record_without_a_discogs_id_has_no_qr(conn):
    rid = records.create(conn, artist="A", title="B")
    assert label_data.build(queries.record_detail(conn, rid)).qr_url is None


# ---- renderer ----

def test_labels_are_62_by_40_mm_one_bit_images():
    images, warnings = label_render.render(sample())
    assert [i.name for i in images] == ["main", "tracks"] and warnings == []
    for image in images:
        img = pixels(image.png)
        assert img.size == (696, 472) and img.mode == "1"  # 62 x 40 mm at 300 dpi, black or white only
        assert round(img.info["dpi"][0]) == 300
        assert 0 < sum(1 for p in img.getdata() if p == 0)  # something was drawn


def test_hiding_a_field_changes_the_label():
    full = label_render.render(sample())[0][0].png
    for field in ("label", "catno", "year", "styles", "note", "qr"):
        assert label_render.render(sample(hidden=[field]))[0][0].png != full, field


def test_editing_a_value_changes_the_label():
    assert (label_render.render(sample(country="UK"))[0][0].png
            != label_render.render(sample())[0][0].png)


def test_main_label_without_a_qr_url_just_has_no_qr():
    assert label_render.render(sample(qr_url=None))[0][0].png == label_render.render(sample(hidden=["qr"]))[0][0].png


def test_long_text_is_cut_and_reported():
    assert warnings_of(sample()) == []
    assert any("title" in w for w in warnings_of(sample(title="Word " * 60)))
    assert any("artist" in w for w in warnings_of(sample(artist="Artist " * 40)))


def test_a_note_that_does_not_fit_is_reported():
    assert any("note" in w for w in warnings_of(sample(note="Very long note. " * 40)))


def test_tracks_are_left_off_when_skipped_or_absent():
    skipped = [LabelTrack(position="A1", skip=True)]
    assert [i.kind for i in label_render.render(sample(skipped))[0]] == ["main"]
    assert [i.kind for i in label_render.render(LabelData(artist="A", title="B", tracks=[]))[0]] == ["main"]


def test_many_tracks_need_several_labels():
    many = [LabelTrack(position=f"{side}{n}", bpm="128", key="8A", tags=["a", "b"], note="note")
            for side in "AB" for n in range(1, 6)]
    images, warnings = label_render.render(sample(many))
    assert [i.name for i in images] == ["main", "tracks-1", "tracks-2"]
    assert warnings == ["Tracks label: The tracks need 2 labels"]


def test_sides_group_tracks_and_sides_are_read_from_positions():
    assert [label_render.side_of(p) for p in ("A1", "B", "AA2", "1-3", "2.1", "")] == [
        "A", "B", "AA", "1", "2", "·"]
    pages = label_render._paginate([LabelTrack(position=p) for p in ("A1", "A2", "B1")])
    assert [[(s, len(t)) for s, t in page] for page in pages] == [[("A", 2), ("B", 1)]]


def test_hidden_track_fields_are_not_drawn():
    base = LabelTrack(position="A1", bpm="130", key="8A", tags=["x"], note="n")
    full = label_render.render(sample([base]))[0][1].png
    for field in ("bpm", "key", "tags", "note"):
        hidden = base.model_copy(update={"hidden": [field]})
        assert label_render.render(sample([hidden]))[0][1].png != full, field


# ---- API ----

def test_get_label_defaults_come_from_the_database(client, record_id):
    body = client.get(f"/api/records/{record_id}/label").json()
    assert body["artist"] == "Jeff Mills" and body["tracks"][0]["key"] == "4A"


def test_label_is_only_for_records_in_the_library(client):
    assert client.get("/api/records/999/label").status_code == 404
    assert client.post("/api/records/999/label/render", json=sample().model_dump()).status_code == 404


def test_render_returns_pngs_and_changes_nothing(client, record_id, conn):
    edited = client.get(f"/api/records/{record_id}/label").json()
    edited["artist"] = "Someone Else"
    edited["country"] = "UK"
    response = client.post(f"/api/records/{record_id}/label/render", json=edited)
    assert response.status_code == 200
    body = response.json()
    assert [i["name"] for i in body["images"]] == ["main", "tracks"] and body["warnings"] == []
    for image in body["images"]:
        assert (image["width"], image["height"]) == (696, 472)
        assert pixels(base64.b64decode(image["png_base64"])).size == (696, 472)
    assert records.get(conn, record_id)["artist"] == "Jeff Mills (2)"  # edits are for this print only


def test_render_rejects_malformed_edits(client, record_id):
    assert client.post(f"/api/records/{record_id}/label/render", json={"artist": "A"}).status_code == 422
    bad = sample().model_dump() | {"hidden": ["nonsense"]}
    assert client.post(f"/api/records/{record_id}/label/render", json=bad).status_code == 422


# ---- labels for records you do not own yet ----

def test_loose_label_renders_without_a_record(client):
    body = sample().model_dump()
    out = client.post("/api/labels/render", json=body)
    assert out.status_code == 200 and out.json()["images"]


def test_label_from_discogs_link_stores_nothing(client):
    out = client.post("/api/labels/from-discogs", json={"discogs_url": "https://www.discogs.com/release/9261843"})
    assert out.status_code == 200
    data = out.json()
    assert data["title"] and data["tracks"] and data["qr_url"].endswith("/9261843")
    assert client.get("/api/records").json()["total"] == 0


def test_label_from_bad_link_is_a_clear_error(client):
    out = client.post("/api/labels/from-discogs", json={"discogs_url": "https://example.com/x"})
    assert out.status_code == 400
