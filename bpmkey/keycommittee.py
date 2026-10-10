"""Features for the committee key model: several Essentia profiles vote on all 24 keys.

Each profile gives one key and a strength. For every candidate key k the model sees, per profile,
whether k *is* that key, is its relative / parallel / a fifth away, plus a mode term. The
relation features are what let a minor-only profile (`edmm`) still support the relative or
parallel major, which a flat "everything else" spread cannot do.
"""
from __future__ import annotations

import numpy as np

SHIPPED_PROFILES, SHIPPED_LAMBDA = ("edmm", "bgate"), 2.0  # what keydetect runs; see benchmark/keymodel_fit.py
ALL_PROFILES = ("edmm", "edma", "bgate", "krumhansl", "temperley", "shaath", "braw")
PER_PROFILE = 5  # match, match x strength, relative, parallel, fifth

_K = np.arange(24)
_TONIC, _MINOR = _K % 12, _K >= 12


def relations(idx: int) -> np.ndarray:
    """5 x 24 indicator rows: how each candidate key relates to key `idx`."""
    t, minor = idx % 12, idx >= 12
    rel_tonic = (t + 3) % 12 if minor else (t + 9) % 12  # relative major of a minor, and vice versa
    return np.stack([
        _K == idx,
        np.zeros(24),  # filled by features(): match x strength
        (_MINOR != minor) & (_TONIC == rel_tonic),
        (_MINOR != minor) & (_TONIC == t),
        (_MINOR == minor) & np.isin((_TONIC - t) % 12, (5, 7)),
    ]).astype(float)


def template_features(chroma: np.ndarray) -> np.ndarray:
    """24 x 24: the chroma read relative to each candidate tonic, in a major block and a minor block.

    Learned weights on this are a data-fitted key profile (it sees the 3rd / 6th / 7th directly).
    """
    c = np.asarray(chroma, dtype=float) * 12 - 1  # centred: 0 = flat chroma
    rolled = np.stack([np.roll(c, -t) for t in range(12)])  # rolled[t][j] = c[(t + j) % 12]
    out = np.zeros((24, 24))
    out[:12, :12] = rolled
    out[12:, 12:] = rolled
    return out


def features(votes: dict[str, tuple[int, float]], profiles=ALL_PROFILES, chroma=None) -> np.ndarray:
    """votes: profile -> (key index, strength). Returns 24 x F. A missing profile contributes zeros.

    With `chroma` (12 values) the data-fitted template block is appended.
    """
    cols = [(~_MINOR).astype(float)[:, None]]  # mode term: candidate is major
    for p in profiles:
        if p not in votes:
            cols.append(np.zeros((24, PER_PROFILE)))
            continue
        idx, strength = votes[p]
        r = relations(idx)
        r[1] = r[0] * (strength - 0.8) * 10
        cols.append(r.T)
    if chroma is not None:
        cols.append(template_features(chroma))
    return np.hstack(cols)


# ---- the previous scheme, kept for benchmarking only -------------------------------------
_STRENGTH = [0.65, 0.76, 0.84, 0.895, 0.95]
_ACCURACY = [0.31, 0.50, 0.73, 0.83, 0.87]


def legacy_probs(votes: dict[str, tuple[int, float]]) -> np.ndarray:
    idx, strength = votes["edmm"]
    p = float(np.interp(strength, _STRENGTH, _ACCURACY))
    probs = np.full(24, (1 - p) / 23)
    probs[idx] = p
    if strength < 0.71 and "bgate" in votes and votes["bgate"][0] != idx:
        probs[votes["bgate"][0]] = min((1 - p) * 0.5, 0.8 * p)
    return probs / probs.sum()
