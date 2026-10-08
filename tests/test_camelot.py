from bpmkey.camelot import to_camelot


def test_formats():
    assert to_camelot("Em") == "9A"
    assert to_camelot("C#m") == "12A"
    assert to_camelot("F♯") == "2B"
    assert to_camelot("Bb minor") == "3A"
    assert to_camelot(("A", "minor")) == "8A"
    assert to_camelot("C major") == "8B"
    assert to_camelot("Abm") == "1A"
    assert to_camelot("B") == "1B"
    assert to_camelot("8a") == "8A"
    assert to_camelot("nonsense") is None
    assert to_camelot(None) is None
