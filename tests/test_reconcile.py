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
