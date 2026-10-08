"""Key estimation for electronic music.

A small transposition-equivariant linear model (74 parameters) over tuned, harmonic-only
constant-Q pitch-class profiles in three frequency bands, trained on human-labelled
GiantSteps-MTG clips. Cross-validated exact-key accuracy on those clips is ~62%, against
~54% for Essentia's default EDM profile and ~58% for its best alternative ("bgate").
It is fused with a bgate vote, which added ~2 points out of fold.

Long tracks are sampled sparsely: up to three 2-minute excerpts spread across the track,
so intros, breakdowns and outros don't dominate.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

SR = 22050
EXCERPT_SECONDS = 120
MAX_EXCERPTS = 3
BPO, N_OCT = 36, 6
BGATE_WEIGHT = 1.0
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_MODEL = Path(__file__).parent / "data" / "key_model.json"


@lru_cache(maxsize=1)
def _weights():
    d = json.loads(_MODEL.read_text())
    return np.array(d["W"], dtype=np.float64), np.array(d["b"], dtype=np.float64)


def index_to_key(i: int) -> tuple[str, str]:
    """Class index (0-11 major, 12-23 minor) -> ('F#', 'minor')."""
    return NAMES[i % 12], "major" if i < 12 else "minor"


def _excerpts(y: np.ndarray, sr: int) -> list[np.ndarray]:
    n = EXCERPT_SECONDS * sr
    if len(y) <= 1.5 * n:
        return [y]
    count = min(MAX_EXCERPTS, int(len(y) // n))
    centres = [(i + 0.5) / count * len(y) for i in range(count)]
    return [y[int(max(0, min(c - n / 2, len(y) - n))):][:n] for c in centres]


def _band_profiles(y: np.ndarray) -> np.ndarray:
    """(3, 12) L2-normalised pitch-class profiles of the harmonic part of `y`."""
    import librosa

    h = librosa.effects.harmonic(y, margin=4)
    tuning = float(librosa.estimate_tuning(y=h, sr=SR, bins_per_octave=BPO))
    fmin = librosa.note_to_hz("C2") * 2 ** (-1 / BPO)
    C = np.abs(librosa.cqt(h, sr=SR, hop_length=2048, fmin=fmin, n_bins=BPO * N_OCT,
                           bins_per_octave=BPO, tuning=tuning))
    semi = C.reshape(N_OCT, 12, 3, -1).sum(axis=2)                      # octave, semitone, time
    bands = np.sqrt(np.stack([semi[0:2].sum(0), semi[2:4].sum(0), semi[4:6].sum(0)]))
    bands = bands / (bands.sum(axis=1, keepdims=True) + 1e-9)           # per frame, per band
    m = bands.mean(axis=2)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)


def log_probs(y: np.ndarray, sr: int = SR) -> np.ndarray:
    """Mean log-probability over the 24 keys, across sparse excerpts of `y`."""
    W, b = _weights()
    out = []
    for ex in _excerpts(y, sr):
        f = _band_profiles(ex)                                           # (3,12)
        rot = np.stack([np.roll(f, -t, axis=1) for t in range(12)])      # (12,3,12)
        s = np.einsum("tbp,mbp->tm", rot, W) + b
        s = np.concatenate([s[:, 0], s[:, 1]])                           # major pcs, minor pcs
        s = s - s.max()
        out.append(s - np.log(np.exp(s).sum()))
    return np.mean(out, axis=0)


def fuse(lp: np.ndarray, bgate_index: int | None) -> np.ndarray:
    """Add Essentia's bgate vote and renormalise to log-probabilities."""
    s = lp.copy()
    if bgate_index is not None:
        s[bgate_index] += BGATE_WEIGHT
    s = s - s.max()
    return s - np.log(np.exp(s).sum())
