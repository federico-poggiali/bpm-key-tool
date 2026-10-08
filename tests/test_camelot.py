from bpmkey.camelot import open_key_to_camelot, to_camelot


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


def test_open_key():
    assert open_key_to_camelot("3d") == "10B"   # D major
    assert open_key_to_camelot("1d") == "8B"    # C major
    assert open_key_to_camelot("1m") == "8A"    # A minor
    assert open_key_to_camelot("12m") == "7A"   # D minor
    assert open_key_to_camelot("x") is None
