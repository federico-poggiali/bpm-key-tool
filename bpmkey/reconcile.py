from __future__ import annotations

from typing import Optional

import numpy as np

from .camelot import camelot_to_key_index, key_index_to_camelot
from .keycommittee import relations
from .models import Measurement, Result, Track

BPM_TOLERANCE = 1.5
# Chance that a database's exact key is right. Estimated from how often GetSongBPM, AcousticBrainz and
# the audio agree on the same tracks (small sample, non-EDM library), then rounded down because their
# errors are not fully independent of the audio's.
DB_RELIABILITY = {"getsongbpm": 0.5, "acousticbrainz": 0.35}
DEFAULT_RELIABILITY = 0.35
# A wrong database key is usually a neighbour of the truth (relative, parallel, fifth); the rest is spread evenly.
NEIGHBOUR_SHARE = 0.5


def db_log_likelihood(key_index: int, reliability: float) -> np.ndarray:
    """log P(database says key_index | true key k) for each of the 24 keys k."""
    near = relations(key_index)[2:].sum(axis=0)  # relative, parallel and the two fifths: 4 keys
    wrong = (1 - NEIGHBOUR_SHARE) / 23 + NEIGHBOUR_SHARE / 4 * near
    lik = (1 - reliability) * wrong
    lik[key_index] = reliability
    return np.log(lik)


def fold_bpm(bpm: float, ref: float) -> float:
    """Return bpm, or bpm x2 / x0.5, whichever is closest to ref."""
    return min((bpm, bpm * 2, bpm / 2), key=lambda b: abs(b - ref))


def _bpm_consensus(ms: list[Measurement]) -> tuple[Optional[float], bool]:
    vals = [m.bpm for m in ms if m.bpm]
    if not vals:
        return None, False
    ref = sorted(vals)[len(vals) // 2]
    folded = [fold_bpm(v, ref) for v in vals]
    agreed = len(folded) > 1 and max(folded) - min(folded) <= BPM_TOLERANCE
    return round(sum(folded) / len(folded), 1), agreed


def reconcile(track: Track) -> Result:
    ms = track.measurements
    bpm, bpm_ok = _bpm_consensus(ms)
    keys = [m.camelot for m in ms if m.camelot]
    key = max(set(keys), key=keys.count) if keys else None
    key_ok = len(keys) > 1 and len(set(keys)) == 1

    bpm_n = sum(1 for m in ms if m.bpm)
    if bpm is None and key is None:
        status = "none"
    elif (bpm_n > 1 and not bpm_ok) or (len(keys) > 1 and not key_ok):
        status = "conflict"
    elif bpm_ok and key_ok:
        status = "agreed"
    else:
        status = "single"
    return Result(track, bpm, key, status)


def needs_analysis(result: Result) -> bool:
    return result.status != "agreed"


def is_analysis(m: Measurement) -> bool:
    return m.origin.startswith("essentia")


def finalize(track: Track) -> Result:
    """Reconcile online sources, then let the audio analysis break ties.

    Online sources that agree with Essentia are kept (and averaged for BPM); otherwise
    the audio analysis wins, because it measured the actual recording.
    """
    online = Track(track.release_id, track.position, track.artist, track.title,
                   track.duration, measurements=[m for m in track.measurements if not is_analysis(m)])
    base = reconcile(online)
    ess = next((m for m in track.measurements if is_analysis(m)), None)
    if ess is None:
        return base

    notes = []
    agreeing = [fold_bpm(m.bpm, ess.bpm) for m in online.measurements
                if m.bpm and abs(fold_bpm(m.bpm, ess.bpm) - ess.bpm) <= BPM_TOLERANCE]
    bpm_ok = bool(agreeing)
    bpm = round(sum(agreeing + [ess.bpm]) / (len(agreeing) + 1), 1)
    online_keys = {m.camelot: m.origin for m in online.measurements if m.camelot}
    key = ess.camelot
    if ess.key_scores:  # audio gave a full distribution: let validated database keys weigh in
        scores = np.array(ess.key_scores, dtype=float)
        for m in online.measurements:
            idx = camelot_to_key_index(m.camelot)
            if idx is not None:
                scores += db_log_likelihood(idx, DB_RELIABILITY.get(m.origin, DEFAULT_RELIABILITY))
        key = key_index_to_camelot(int(scores.argmax()))
    key_ok = key in online_keys
    if key_ok:
        notes.append(f"key confirmed by {online_keys[key]}")
    elif online_keys:
        notes.append("online keys " + "/".join(sorted(online_keys)) + " outvoted by audio")
    if not bpm_ok and any(m.bpm for m in online.measurements):
        notes.append("online BPM rejected by audio")
    status = "agreed" if (bpm_ok or not any(m.bpm for m in online.measurements)) and key_ok else "analyzed"
    return Result(track, bpm, key, status, "; ".join(notes))
