"""Mean pitch-class profile of a track, used as a direct mode cue (third / sixth / seventh)."""
from __future__ import annotations

import numpy as np

CHROMA_SR = 22050
CHROMA_SECONDS = 150  # centre slice: enough for a stable profile, keeps long tracks cheap


def mean_chroma(audio: np.ndarray, sr: int = 44100) -> np.ndarray:
    """12 values summing to 1, index 0 = C. `audio` is mono at `sr`."""
    import librosa

    n = CHROMA_SECONDS * sr
    if len(audio) > n:
        start = (len(audio) - n) // 2
        audio = audio[start:start + n]

    y = librosa.resample(audio, orig_sr=sr, target_sr=CHROMA_SR) if sr != CHROMA_SR else audio
    c = librosa.feature.chroma_cqt(y=y, sr=CHROMA_SR, tuning=0.0).mean(axis=1)
    return c / max(float(c.sum()), 1e-9)
