import numpy as np
import pytest

from bpmkey import keydetect


def _chord(freqs, secs=20, sr=44100):
    t = np.arange(sr * secs) / sr
    return (sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs) * 0.5).astype(np.float32)


def test_accuracy_is_monotonic_and_clamped():
    assert keydetect.accuracy_at(0.0) == keydetect._ACCURACY[0]
    assert keydetect.accuracy_at(1.0) == keydetect._ACCURACY[-1]
    assert keydetect.accuracy_at(0.6) <= keydetect.accuracy_at(0.8) <= keydetect.accuracy_at(0.9)


def test_scores_are_a_distribution_peaked_on_the_estimate():
    pytest.importorskip("essentia")
    a_minor = _chord([220.0, 261.63, 329.63])  # A C E
    est = keydetect.detect(a_minor)
    assert abs(np.exp(est.scores).sum() - 1) < 1e-6
    assert est.scores.argmax() == est.index
    assert est.source == "edmm"


def test_falls_back_to_backup_when_primary_fails(monkeypatch):
    calls = []

    def fake(profile, audio):
        calls.append(profile)
        if profile == keydetect.PRIMARY:
            raise RuntimeError("boom")
        return 5, 0.9

    monkeypatch.setattr(keydetect, "_run", fake)
    est = keydetect.detect(np.zeros(10, dtype=np.float32))
    assert est.source == keydetect.BACKUP and est.index == 5
    assert calls == [keydetect.PRIMARY, keydetect.BACKUP]


def test_doubt_shares_mass_with_backup_without_overruling(monkeypatch):
    monkeypatch.setattr(keydetect, "_run", lambda profile, audio: (0, 0.5) if profile == "edmm" else (7, 0.9))
    est = keydetect.detect(np.zeros(10, dtype=np.float32))
    assert est.in_doubt and est.index == 0 and est.scores.argmax() == 0
    assert est.scores[7] > est.scores[3]  # backup's key is the runner-up
