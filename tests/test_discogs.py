from bpmkey.discogs import parse_duration, parse_tracklist, parse_url


def test_parse_url():
    assert parse_url("https://www.discogs.com/release/249504-Rick-Astley-Never") == ("release", 249504)
    assert parse_url("https://www.discogs.com/master/96559") == ("master", 96559)


def test_parse_duration():
    assert parse_duration("5:32") == 332
    assert parse_duration("1:02:03") == 3723
    assert parse_duration("") is None
    assert parse_duration("abc") is None


def test_tracklist_handles_headings_indexes_and_artists():
    data = {
        "artists": [{"name": "Foo (2)", "join": ""}],
        "tracklist": [
            {"type_": "heading", "title": "Side A"},
            {"type_": "track", "position": "A1", "title": "One", "duration": "4:00"},
            {"type_": "track", "position": "A2", "title": "Two", "duration": "",
             "artists": [{"name": "Bar", "join": "&"}, {"name": "Baz", "join": ""}]},
            {"type_": "index", "title": "Suite", "sub_tracks": [
                {"type_": "track", "position": "B1a", "title": "Part 1", "duration": "1:00"}]},
        ],
    }
    t = parse_tracklist(data, 1)
    assert [x.position for x in t] == ["A1", "A2", "B1a"]
    assert t[0].artist == "Foo" and t[0].duration == 240
    assert t[1].artist == "Bar & Baz" and t[1].duration is None
