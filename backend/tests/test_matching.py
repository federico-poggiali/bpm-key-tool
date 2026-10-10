from pathlib import Path

from app.analysis.matching import file_position, match_files, normalize_position

TRACKS = [
    {"id": 1, "position": "A1", "title": "One More Time"},
    {"id": 2, "position": "A2", "title": "Aerodynamic"},
    {"id": 3, "position": "B1", "title": "Digital Love"},
]


def files(*names):
    return [Path(n) for n in names]


def test_position_parsing():
    assert file_position("A1 - One More Time") == "A1"
    assert file_position("a01_title") == "A1"
    assert file_position("B2.wav".removesuffix(".wav")) == "B2"
    assert file_position("1-03 Song") == "1-3"
    assert file_position("Aerodynamic") is None
    assert normalize_position("A01") == "A1"


def test_matches_by_position_then_title():
    report = match_files(files("A1 - whatever.wav", "a2.flac", "Digital Love.mp3"), TRACKS)
    by_track = {m["track_id"]: m for m in report["matched"]}
    assert by_track[1]["method"] == "position"
    assert by_track[2]["method"] == "position"
    assert by_track[3]["method"] == "title"
    assert report["unmatched_files"] == [] and report["unmatched_tracks"] == []


def test_mismatched_files_and_tracks_are_reported():
    report = match_files(files("A1 - One More Time.wav", "zzz random.wav", "C9 - nothing.wav"), TRACKS)
    assert [m["track_id"] for m in report["matched"]] == [1]
    assert {u["file"] for u in report["unmatched_files"]} == {"zzz random.wav", "C9 - nothing.wav"}
    assert {t["track_id"] for t in report["unmatched_tracks"]} == {2, 3}


def test_duplicate_position_claims_are_not_guessed():
    report = match_files(files("A1 - one.wav", "A1 - two.wav"), TRACKS)
    assert report["matched"] == []
    assert len(report["unmatched_files"]) == 2
    assert all("several files" in u["reason"] for u in report["unmatched_files"])


def test_ambiguous_title_is_not_guessed():
    tracks = [{"id": 1, "position": "A1", "title": "Mix Part 1"},
              {"id": 2, "position": "A2", "title": "Mix Part 2"}]
    report = match_files(files("Mix Part.wav"), tracks)
    assert report["matched"] == []
    assert report["unmatched_files"][0]["reason"] == "title matches several tracks"
