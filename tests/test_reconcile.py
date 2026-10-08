from bpmkey.matching import is_match
from bpmkey.models import Measurement, Track
from bpmkey.reconcile import reconcile


def mk(*ms):
    t = Track(1, "A1", "x", "y")
    t.measurements = list(ms)
    return t


def test_agreed_with_half_double_fold():
    r = reconcile(mk(Measurement("a", 124, "8A"), Measurement("b", 62.2, "8A")))
    assert r.status == "agreed" and r.camelot == "8A" and abs(r.bpm - 124.1) < 0.2


def test_key_conflict():
    assert reconcile(mk(Measurement("a", 124, "8A"), Measurement("b", 124, "9A"))).status == "conflict"


def test_single_and_none():
    assert reconcile(mk(Measurement("a", 124, None))).status == "single"
    assert reconcile(mk()).status == "none"


def test_matching():
    assert is_match("Daft Punk", "One More Time", "Daft Punk", "One More Time (Radio Edit)")
    assert not is_match("Daft Punk", "One More Time", "Daft Punk", "Around The World")


def test_score_candidate_rules():
    from bpmkey.matching import score_candidate as sc
    assert sc("Jlin", "Black Origami", 271, "Jlin - Black Origami", "", 272) >= 0.9
    assert sc("Jlin", "Black Origami", 271, "Jlin - Black Origami", "", 400) == 0.0   # wrong length
    assert sc("Jlin", "Black Origami", None, "Jlin - Black Origami", "", 2676) == 0.0  # DJ mix
    assert sc("Jlin", "Black Origami", 271, "Jlin - Black Origami (Remix)", "", 271) < 0.75


def test_is_match_rejects_wrong_song_and_other_versions():
    from bpmkey.matching import is_match
    assert not is_match("Arca", "Whip", "Jade Arcade", "Whipping Post")
    assert not is_match("The Prodigy", "Your Love", "The Prodigy", "Your Love (remix)")
    assert is_match("Moby", "Drop A Beat", "Moby", "Drop a Beat")
    assert is_match("The Prodigy", "Charly (Alley Cat Remix)", "The Prodigy", "Charly (Alley Cat Remix)")


def test_harmless_version_labels():
    from bpmkey.matching import is_match
    assert is_match("A", "Title", "A", "Title (Original Mix)")
    assert is_match("A", "Title (Original Mix)", "A", "Title")
    assert not is_match("A", "Title", "A", "Title (Dub Mix)")
