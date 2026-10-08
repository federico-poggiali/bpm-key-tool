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


def test_database_vote_can_flip_a_close_audio_call():
    import numpy as np
    from bpmkey.camelot import camelot_to_key_index
    scores = np.full(24, -6.0)
    scores[camelot_to_key_index("8A")] = -0.6     # audio's favourite
    scores[camelot_to_key_index("10B")] = -1.0    # close second
    r = finalize(mk(Measurement("getsongbpm", 122, "10B"),
                    Measurement("essentia:youtube", 122.5, "8A", key_scores=scores.tolist())))
    assert r.camelot == "10B" and "confirmed by getsongbpm" in r.note


def test_confident_audio_beats_a_database_vote():
    import numpy as np
    from bpmkey.camelot import camelot_to_key_index
    scores = np.full(24, -8.0)
    scores[camelot_to_key_index("8A")] = -0.05
    r = finalize(mk(Measurement("getsongbpm", 122, "10B"),
                    Measurement("essentia:youtube", 122.5, "8A", key_scores=scores.tolist())))
    assert r.camelot == "8A" and "outvoted" in r.note
