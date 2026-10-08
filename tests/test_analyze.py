import numpy as np
import pytest

from bpmkey.analyze import analyze_file, clamp_bpm


def test_clamp_bpm():
    assert clamp_bpm(62) == 124
    assert clamp_bpm(248) == 124
    assert clamp_bpm(128) == 128


def _write_wav(path, samples, sr=44100):
    import wave
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def test_synthetic_click_track(tmp_path):
    pytest.importorskip("essentia")
    sr, bpm, secs = 44100, 120, 40
    t = np.arange(sr * secs) / sr
    sig = 0.3 * np.sin(2 * np.pi * 220 * t)  # A3 drone
    for b in np.arange(0, secs, 60 / bpm):   # kick-like clicks
        i = int(b * sr)
        n = min(2000, len(sig) - i)
        sig[i:i + n] += np.hanning(n) * np.sin(2 * np.pi * 60 * np.arange(n) / sr)
    f = tmp_path / "click.wav"
    _write_wav(f, sig)
    m = analyze_file(f)
    assert abs(m.bpm - 120) <= 3 or abs(m.bpm - 60) <= 3 or abs(m.bpm - 240) <= 6
    assert m.origin == "essentia" and m.camelot
