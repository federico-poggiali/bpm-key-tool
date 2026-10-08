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
    key_ok = key in online_keys
    if key_ok:
        notes.append(f"key confirmed by {online_keys[key]}")
    elif online_keys:
        notes.append("online keys " + "/".join(sorted(online_keys)) + " rejected by audio")
    if not bpm_ok and any(m.bpm for m in online.measurements):
        notes.append("online BPM rejected by audio")
    status = "agreed" if (bpm_ok or not any(m.bpm for m in online.measurements)) and key_ok else "analyzed"
    return Result(track, bpm, key, status, "; ".join(notes))
