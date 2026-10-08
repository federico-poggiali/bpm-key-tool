from bpmkey.models import Measurement, Track
from bpmkey.reconcile import finalize


def mk(*ms):
    t = Track(1, "A1", "x", "y")
    t.measurements = list(ms)
    return t


def test_audio_confirms_online_key_and_bpm():
    r = finalize(mk(Measurement("getsongbpm", 122, "10B"), Measurement("acousticbrainz", 126.7, "9B"),
                    Measurement("essentia:youtube", 122.9, "10B", confidence=0.86)))
    assert r.status == "agreed" and r.camelot == "10B" and abs(r.bpm - 122.45) < 0.1
    assert "confirmed by getsongbpm" in r.note


def test_audio_overrules_wrong_online_values():
    r = finalize(mk(Measurement("deezer", 90, None), Measurement("acousticbrainz", 90, "4A"),
                    Measurement("essentia:itunes", 128.0, "8A")))
    assert r.status == "analyzed" and r.camelot == "8A" and r.bpm == 128.0


def test_no_audio_falls_back_to_online():
    assert finalize(mk(Measurement("deezer", 120, None))).status == "single"
