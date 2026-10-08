from __future__ import annotations

from typing import Optional

from .models import Measurement, Result, Track

BPM_TOLERANCE = 1.5


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
