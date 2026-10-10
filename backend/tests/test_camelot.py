import pytest

from app.analysis.camelot import to_camelot


@pytest.mark.parametrize("key,expected", [
    ("A minor", "8A"), ("Am", "8A"), ("C major", "8B"), ("C", "8B"), ("F# minor", "11A"),
    ("Gb major", "2B"), ("Bb minor", "3A"), ("E♭ major", "5B"), ("8A", "8A"), ("12b", "12B"),
])
def test_to_camelot(key, expected):
    assert to_camelot(key) == expected


def test_to_camelot_rejects_garbage():
    assert to_camelot("nonsense") is None
    assert to_camelot(None) is None
