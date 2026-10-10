import numpy as np
import pytest

from bpmkey import keydetect


def _chord(freqs, secs=20, sr=44100):
    t = np.arange(sr * secs) / sr
    return (sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs) * 0.5).astype(np.float32)


def _chroma(pitch_classes):
    c = np.full(12, 0.3)
    c[list(pitch_classes)] += 1.0
    return c / c.sum()


C_MAJOR, A_MINOR = _chroma([0, 4, 7]), _chroma([9, 0, 4])
AM, CMAJ, CM = 21, 0, 12  # key indices: 0-11 major, 12-23 minor


def test_scores_are_a_distribution_peaked_on_the_estimate():
    pytest.importorskip("essentia")
    est = keydetect.detect(_chord([220.0, 261.63, 329.63]))  # A C E
    assert abs(np.exp(est.scores).sum() - 1) < 1e-6
    assert est.scores.argmax() == est.index
    assert est.source == "edmm+bgate"


def test_a_major_key_is_reachable_although_edmm_only_says_minor():
    # edmm names the relative minor, but bgate and the chroma both say C major
    p = keydetect.posterior({"edmm": (AM, 0.8), "bgate": (CMAJ, 0.8)}, C_MAJOR, prior_shift=0)
    assert p.argmax() == CMAJ and p[:12].sum() > 0.7


def test_parallel_minor_from_edmm_alone_can_be_corrected_by_chroma():
    p = keydetect.posterior({"edmm": (CM, 0.8)}, C_MAJOR, prior_shift=0)
    assert p.argmax() == CMAJ


def test_clear_minor_evidence_stays_minor():
    p = keydetect.posterior({"edmm": (AM, 0.8), "bgate": (AM, 0.8)}, A_MINOR, prior_shift=0)
    assert p.argmax() == AM


def test_prior_shift_moves_probability_towards_major_only():
    votes = {"edmm": (AM, 0.8), "bgate": (CMAJ, 0.8)}
    lo, hi = (keydetect.posterior(votes, A_MINOR, prior_shift=s) for s in (0, 2))
    assert hi[:12].sum() > lo[:12].sum()
    assert hi.sum() == pytest.approx(1)


def test_a_failing_profile_drops_out_of_the_committee(monkeypatch):
    def fake(profile, audio):
        if profile == "edmm":
            raise RuntimeError("boom")
        return AM, 0.9

    monkeypatch.setattr(keydetect, "_run", fake)
    monkeypatch.setattr(keydetect.keychroma, "mean_chroma", lambda audio: A_MINOR)
    est = keydetect.detect(np.zeros(10, dtype=np.float32))
    assert est.source == "bgate" and est.index == AM


def test_all_profiles_failing_raises(monkeypatch):
    monkeypatch.setattr(keydetect, "_run", lambda profile, audio: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(ValueError):
        keydetect.detect(np.zeros(10, dtype=np.float32))


def test_estimate_survives_a_chroma_failure(monkeypatch):
    monkeypatch.setattr(keydetect, "_run", lambda profile, audio: (AM, 0.9))

    def boom(audio):
        raise RuntimeError("no chroma")

    monkeypatch.setattr(keydetect.keychroma, "mean_chroma", boom)
    assert keydetect.detect(np.zeros(10, dtype=np.float32)).index == AM
