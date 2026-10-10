import pytest

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


def test_two_agreeing_databases_can_overrule_a_moderate_audio_call():
    import numpy as np
    from bpmkey.camelot import camelot_to_key_index
    scores = np.full(24, -4.5)
    scores[camelot_to_key_index("8A")] = -0.5   # audio says A minor with ~85%
    r = finalize(mk(Measurement("getsongbpm", 122, "10B"), Measurement("acousticbrainz", 122, "10B"),
                    Measurement("essentia:youtube", 122.5, "8A", key_scores=scores.tolist())))
    assert r.camelot == "10B"


def test_a_database_likelihood_is_a_distribution_over_what_it_can_report():
    import numpy as np
    from bpmkey.reconcile import db_log_likelihood
    # for any true key, the probabilities of every key the database might report sum to 1
    for true_key in (0, 9, 15, 23):
        total = sum(np.exp(db_log_likelihood(d, 0.4))[true_key] for d in range(24))
        assert total == pytest.approx(1.0)


def test_wrong_database_keys_are_more_likely_next_door_than_far_away():
    import numpy as np
    from bpmkey.camelot import camelot_to_key_index
    from bpmkey.reconcile import db_log_likelihood
    ll = db_log_likelihood(camelot_to_key_index("8A"), 0.5)
    assert ll[camelot_to_key_index("8A")] > ll[camelot_to_key_index("8B")] > ll[camelot_to_key_index("2A")]


def test_dynamic_threshold_for_discogs_videos():
    from bpmkey.matching import dynamic_threshold
    assert dynamic_threshold(["Rodney King (Da Falcon Mix)", "Live In The World"]) == pytest.approx(0.55, abs=0.08)
    assert dynamic_threshold(["Song (Original Mix)", "Song (Dub Mix)"]) == pytest.approx(0.95)
    assert dynamic_threshold(["Only Track"]) == pytest.approx(0.55)


def test_finders_share_the_release_threshold():
    from bpmkey.sources import finders_for
    unrelated = {"tracklist": [{"title": "Rodney King"}, {"title": "Live In The World"}]}
    remixes = {"tracklist": [{"title": "Song (Original Mix)"}, {"title": "Song (Dub Mix)"}]}
    yt, sc, itunes = finders_for(unrelated)
    assert yt.threshold == sc.threshold < 0.6
    assert itunes.threshold == 0.75  # previews keep the strict bar
    yt, sc, _ = finders_for(remixes)
    assert yt.threshold == sc.threshold == pytest.approx(0.95)
