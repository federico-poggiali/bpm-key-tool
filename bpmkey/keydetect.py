"""Key detection: Essentia KeyExtractor with the EDM profile `edmm`, `bgate` as backup.

Benchmarked on GiantSteps Key (604 human-labelled Beatport clips): `edmm` 65% exact key,
weighted score 0.70; `bgate` 61% / 0.68. Switching to `bgate` when `edmm` is unsure never
helped on that set (even where `edmm` is weak, `bgate` is no better), so the backup is used
when `edmm` fails, and otherwise only to share probability mass when `edmm` is in doubt.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PRIMARY, BACKUP = "edmm", "bgate"
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# edmm exact-key accuracy per KeyExtractor strength on GiantSteps (bucket midpoint -> accuracy)
_STRENGTH = [0.65, 0.76, 0.84, 0.895, 0.95]
_ACCURACY = [0.31, 0.50, 0.73, 0.83, 0.87]
DOUBT_BELOW = 0.71  # strength under which edmm was right less than ~1 time in 3
BACKUP_SHARE = 0.5  # share of the remaining probability given to the backup's key


@dataclass
class KeyEstimate:
    index: int  # 0-11 major, 12-23 minor, by pitch class
    scores: np.ndarray  # 24 log-probabilities
    confidence: float
    source: str  # "edmm" | "bgate"
    in_doubt: bool


def _run(profile: str, audio: np.ndarray) -> tuple[int, float]:
    import essentia.standard as es

    key, scale, strength = es.KeyExtractor(profileType=profile)(audio)
    flat = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
    idx = NAMES.index(flat.get(key, key)) + (12 if scale == "minor" else 0)
    if not np.isfinite(strength):
        raise ValueError("no key strength")
    return idx, float(strength)


def accuracy_at(strength: float) -> float:
    """Calibrated probability that edmm is right at this KeyExtractor strength."""
    return float(np.interp(strength, _STRENGTH, _ACCURACY))


def detect(audio: np.ndarray) -> KeyEstimate:
    try:
        idx, strength = _run(PRIMARY, audio)
        source = PRIMARY
    except Exception:  # primary failed: fall back to the backup profile
        idx, strength = _run(BACKUP, audio)
        source = BACKUP
    p = accuracy_at(strength)
    in_doubt = strength < DOUBT_BELOW
    probs = np.full(24, (1 - p) / 23)
    probs[idx] = p
    if in_doubt and source == PRIMARY:  # let the backup's opinion carry weight, without overruling
        try:
            b_idx, _ = _run(BACKUP, audio)
        except Exception:
            b_idx = idx
        if b_idx != idx:
            probs[b_idx] = min((1 - p) * BACKUP_SHARE, 0.8 * p)
    probs /= probs.sum()
    scores = np.log(probs)
    return KeyEstimate(idx, scores, float(probs[idx]), source, in_doubt)
