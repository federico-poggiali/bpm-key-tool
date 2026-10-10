"""Key detection: a small committee model over Essentia's `edmm` and `bgate` profiles plus chroma.

`edmm` is the most accurate profile on GiantSteps Key (65% exact) but it can only answer minor,
so on its own it is blind to every major key (15% of that set, and probably more of a general
record collection). The committee instead scores all 24 keys from: each profile's key and strength
(and which keys are its relative / parallel / fifth), plus the mean chroma read against each
candidate tonic (a data-fitted key profile that sees the 3rd, 6th and 7th directly). The weights
come from `benchmark/keymodel_fit.py` (conditional logit, cross-validated on GiantSteps).

Cross-validated on GiantSteps: log-loss 1.59 -> 1.31, mode AUC 0.72 -> 0.78, exact 65% -> 66%.
MODE_PRIOR_SHIFT corrects for GiantSteps being 85% minor; see the README for the trade-off.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import keychroma, keycommittee

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
_MODEL = json.loads((Path(__file__).parent / "data" / "key_committee.json").read_text())
PROFILES = tuple(_MODEL["profiles"])
THETA = np.array(_MODEL["theta"])
# Extra log-odds on major keys. 0 keeps GiantSteps' own 85% minor prior; +1.0 assumes ~1 in 3 tracks
# is major, which roughly doubles major recall there (23% -> 43%) for ~3 points of exact accuracy.
MODE_PRIOR_SHIFT = 1.0
DOUBT_BELOW = 0.45  # top-key probability under which the estimate is a coin flip between neighbours


@dataclass
class KeyEstimate:
    index: int  # 0-11 major, 12-23 minor, by pitch class
    scores: np.ndarray  # 24 log-probabilities
    confidence: float
    source: str  # profiles that contributed, e.g. "edmm+bgate"
    in_doubt: bool


def _run(profile: str, audio: np.ndarray) -> tuple[int, float]:
    import essentia.standard as es

    key, scale, strength = es.KeyExtractor(profileType=profile)(audio)
    idx = NAMES.index(_FLAT.get(key, key)) + (12 if scale == "minor" else 0)
    if not np.isfinite(strength):
        raise ValueError("no key strength")
    return idx, float(strength)


def posterior(votes: dict[str, tuple[int, float]], chroma: np.ndarray | None,
              prior_shift: float = MODE_PRIOR_SHIFT) -> np.ndarray:
    """24 probabilities from the profiles' votes and the mean chroma."""
    if chroma is None:  # the template block is zeros; its weights then contribute nothing
        chroma = np.full(12, 1 / 12)
    z = keycommittee.features(votes, PROFILES, chroma) @ THETA
    z[:12] += prior_shift
    z -= z.max()
    p = np.exp(z)
    return p / p.sum()


def detect(audio: np.ndarray) -> KeyEstimate:
    votes = {}
    for profile in PROFILES:
        try:
            votes[profile] = _run(profile, audio)
        except Exception:  # a failing profile just drops out of the committee
            pass
    if not votes:
        raise ValueError("no key profile could analyse this audio")
    try:
        chroma = keychroma.mean_chroma(audio)
    except Exception:
        chroma = None
    p = posterior(votes, chroma)
    idx = int(p.argmax())
    return KeyEstimate(idx, np.log(p), float(p[idx]), "+".join(votes), float(p[idx]) < DOUBT_BELOW)
