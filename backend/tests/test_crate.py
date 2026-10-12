import pytest

from app.db import connect, crate, records, tags


@pytest.fixture
def library(db_path):
    conn = connect(db_path)
    jazz = records.create(conn, artist="Miles Davis", title="Kind of Blue", styles=["Modal", "Hard Bop"])
    house = records.create(conn, artist="The Black Madonna", title="We Still Believe", styles=["Deep House"])
    tags.create_tag(conn, 3, "warm-up")
    tags.add(conn, "record", house, "warm-up")
    want = records.create(conn, artist="Wanted", title="Not Here", status="wantlist")
    conn.close()
    return {"jazz": jazz, "house": house, "want": want}


def crate_ok(resp, status=200):
    assert resp.status_code == status, resp.text
    return resp.json()


def sections(body):
    return [s for u in body["units"] for c in u["cubes"] for s in c["sections"]]


def test_unit_is_made_of_cubes_with_one_section_each(client, library):
    body = crate_ok(client.post("/api/crate/units", json={"name": "Kallax", "rows": 2, "cols": 2}), 201)
    unit = body["units"][0]
    assert [(c["row"], c["col"]) for c in unit["cubes"]] == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert all(len(c["sections"]) == 1 for c in unit["cubes"])
    # every owned record starts unsorted; the wantlist is never on the shelf
    assert {r["id"] for r in body["unsorted"]} == {library["jazz"], library["house"]}


def test_units_cannot_overlap(client, library):
    crate_ok(client.post("/api/crate/units", json={"name": "A", "rows": 2, "cols": 2}), 201)
    assert client.post("/api/crate/units", json={"name": "B", "rows": 1, "cols": 1, "x": 1, "y": 1}).status_code == 409
    body = crate_ok(client.post("/api/crate/units", json={"name": "B", "rows": 1, "cols": 1, "x": 2}), 201)
    b = next(u for u in body["units"] if u["name"] == "B")
    assert client.patch(f"/api/crate/units/{b['id']}", json={"x": 1}).status_code == 409
    assert crate_ok(client.patch(f"/api/crate/units/{b['id']}", json={"x": 3, "y": 4}))


def test_place_and_unsort(client, library):
    body = crate_ok(client.post("/api/crate/units", json={"name": "Kallax", "rows": 1, "cols": 2}), 201)
    first = sections(body)[0]["id"]
    body = crate_ok(client.put("/api/crate/place", json={"record_ids": [library["jazz"]], "section_id": first}))
    assert [r["title"] for r in sections(body)[0]["records"]] == ["Kind of Blue"]
    assert [r["id"] for r in body["unsorted"]] == [library["house"]]
    body = crate_ok(client.put("/api/crate/place", json={"record_ids": [library["jazz"]], "section_id": None}))
    assert len(body["unsorted"]) == 2
    assert client.put("/api/crate/place", json={"record_ids": [999], "section_id": first}).status_code == 404
    assert client.put("/api/crate/place", json={"record_ids": [library["jazz"]], "section_id": 999}).status_code == 404


def test_dividers_add_and_merge_back(client, library):
    body = crate_ok(client.post("/api/crate/units", json={"name": "Eket", "rows": 1, "cols": 1}), 201)
    cube = body["units"][0]["cubes"][0]
    body = crate_ok(client.post(f"/api/crate/cubes/{cube['id']}/sections", json={"name": "N–Z"}), 201)
    left, right = sections(body)
    assert right["name"] == "N–Z" and right["position"] == 1
    crate_ok(client.put("/api/crate/place", json={"record_ids": [library["jazz"]], "section_id": right["id"]}))
    body = crate_ok(client.delete(f"/api/crate/sections/{right['id']}"))
    assert [r["id"] for r in sections(body)[0]["records"]] == [library["jazz"]]  # merged into the left one
    assert client.delete(f"/api/crate/sections/{left['id']}").status_code == 409  # a cube keeps one


def test_shrinking_or_deleting_a_unit_unsorts_its_records(client, library):
    body = crate_ok(client.post("/api/crate/units", json={"name": "Kallax", "rows": 2, "cols": 2}), 201)
    unit = body["units"][0]
    last = unit["cubes"][-1]["sections"][0]["id"]
    crate_ok(client.put("/api/crate/place", json={"record_ids": [library["jazz"]], "section_id": last}))
    body = crate_ok(client.patch(f"/api/crate/units/{unit['id']}", json={"rows": 1}))
    assert len(body["units"][0]["cubes"]) == 2
    assert library["jazz"] in [r["id"] for r in body["unsorted"]]
    body = crate_ok(client.patch(f"/api/crate/units/{unit['id']}", json={"rows": 3, "cols": 3}))
    assert len(body["units"][0]["cubes"]) == 9
    first = body["units"][0]["cubes"][0]["sections"][0]["id"]
    crate_ok(client.put("/api/crate/place", json={"record_ids": [library["house"]], "section_id": first}))
    assert client.delete(f"/api/crate/units/{unit['id']}").status_code == 204
    assert len(crate_ok(client.get("/api/crate"))["unsorted"]) == 2


def test_cube_names_drive_suggestions(client, library):
    body = crate_ok(client.post("/api/crate/units", json={"name": "Kallax", "rows": 1, "cols": 3}), 201)
    jazz_cube, house_cube, warm_cube = body["units"][0]["cubes"]
    crate_ok(client.patch(f"/api/crate/cubes/{jazz_cube['id']}", json={"name": "Jazz", "description": "hard bop, modal"}))
    crate_ok(client.patch(f"/api/crate/cubes/{house_cube['id']}", json={"name": "House"}))
    body = crate_ok(client.patch(f"/api/crate/cubes/{warm_cube['id']}", json={"name": "Warm-up", "description": "deep house"}))
    hints = {r["id"]: r["suggestion"] for r in body["unsorted"]}
    assert hints[library["jazz"]]["section_id"] == jazz_cube["sections"][0]["id"]
    assert set(hints[library["jazz"]]["reasons"]) == {"Modal", "Hard Bop"}
    # tag 'warm-up' and style 'Deep House' both named in full beat 'House' sharing one word
    assert hints[library["house"]]["section_id"] == warm_cube["sections"][0]["id"]


def test_letter_ranges_match_the_artist_initial():
    places = [{"section_id": 1, "labels": ["Soul", "", "", "A–L"]},
              {"section_id": 2, "labels": ["Soul", "", "", "M-Z"]}]
    miles = {"artist": "Miles Davis", "tags": [], "styles": []}
    assert crate.suggest(miles, places)["section_id"] == 2
    the_band = {"artist": "The Black Madonna", "tags": [], "styles": []}  # filed under B
    assert crate.suggest(the_band, places)["section_id"] == 1
    assert crate.suggest({"artist": "Ö", "tags": [], "styles": ["Polka"]}, [{"section_id": 3, "labels": ["Jazz"]}]) is None
