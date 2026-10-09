"""Key-detection methods under test. Each takes (audio_16k_or_44k_array provider) -> (key_name, mode).

All methods share the signature  detect(path) -> "C#:minor"  style tuple (tonic sharps, mode).
"""
from __future__ import annotations

import functools
from pathlib import Path

import numpy as np

SR = 44100
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}


def _norm(key: str, scale: str) -> tuple[str, str]:
    return FLAT.get(key, key), "minor" if scale.lower().startswith("min") else "major"


@functools.lru_cache(maxsize=4)
def load(path: str, sr: int = SR) -> np.ndarray:
    import essentia.standard as es
    return es.MonoLoader(filename=path, sampleRate=sr)()


def _trim(y: np.ndarray, seconds: int = 8 * 60) -> np.ndarray:
    n = seconds * SR
    return y if len(y) <= n else y[(len(y) - n) // 2:(len(y) - n) // 2 + n]


# ---- M1: Krumhansl-Schmuckler on librosa chroma -------------------------------------------
KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def ks_from_chroma(chroma: np.ndarray) -> tuple[str, str]:
    v = chroma.mean(axis=1)
    best, arg = -2, (0, "major")
    for mode, prof in (("major", KS_MAJOR), ("minor", KS_MINOR)):
        for k in range(12):
            r = np.corrcoef(v, np.roll(prof, k))[0, 1]
            if r > best:
                best, arg = r, (k, mode)
    return NOTES[arg[0]], arg[1]


def m1_ks(kind: str):
    def f(path: str):
        import librosa
        y = _trim(load(path))
        y = librosa.resample(y, orig_sr=SR, target_sr=22050)
        c = (librosa.feature.chroma_cqt(y=y, sr=22050) if kind == "cqt"
             else librosa.feature.chroma_stft(y=y, sr=22050))
        return ks_from_chroma(c)
    return f


# ---- M2/M3: Essentia KeyExtractor with a given profile --------------------------------------
def key_extractor(profile: str, harmonic: int | None = None):
    def f(path: str):
        import essentia.standard as es
        y = _trim(load(path))
        if harmonic:
            import librosa
            y = librosa.effects.harmonic(y, margin=harmonic).astype(np.float32)
        key, scale, _ = es.KeyExtractor(profileType=profile)(y)
        return _norm(key, scale)
    return f


# ---- M4: HPCP 36 bins + Key (mirrors Essentia's KeyExtractor chain), optional tuning/multi-profile
def hpcp36(profile: str, majmin: bool = False, detune: bool = True):
    def f(path: str):
        import essentia.standard as es
        y = _trim(load(path))
        w, sp = es.Windowing(type="blackmanharris62"), es.Spectrum()
        peaks = es.SpectralPeaks(orderBy="magnitude", magnitudeThreshold=1e-5, minFrequency=25,
                                 maxFrequency=3500, maxPeaks=60, sampleRate=SR)
        whiten = es.SpectralWhitening(maxFrequency=3500, sampleRate=SR)
        frames = []
        for fr in es.FrameGenerator(y, frameSize=4096, hopSize=4096):
            spec = sp(w(fr))
            fq, mg = peaks(spec)
            if len(fq):
                frames.append((fq, whiten(spec, fq, mg)))
        if not frames:
            raise RuntimeError("no peaks")
        ref = 440.0
        if detune:
            tf = es.TuningFrequency()
            cents = [tf(fq, mg)[0] for fq, mg in frames[::4]]
            ref = float(np.median(cents))
        hp = es.HPCP(size=36, referenceFrequency=ref, bandPreset=False, minFrequency=25,
                     maxFrequency=3500, weightType="squaredCosine", windowSize=4.0 / 3.0,
                     nonLinear=False, sampleRate=SR)
        avg = np.mean([hp(fq, mg) for fq, mg in frames], axis=0).astype(np.float32)
        key, scale, _, _ = es.Key(profileType=profile, numHarmonics=4, pcpSize=36,
                                  useMajMin=majmin)(avg)
        return _norm(key, scale)
    return f


# ---- M9: bass + treble chroma weighting ---------------------------------------------------
def bass_treble(bass_weight: float, profile: str = "krumhansl"):
    def f(path: str):
        import librosa
        y = _trim(load(path))
        y = librosa.resample(y, orig_sr=SR, target_sr=22050)
        C = np.abs(librosa.cqt(y, sr=22050, fmin=librosa.note_to_hz("C1"), n_bins=72,
                               bins_per_octave=12))
        # C1..B6: bass = C2..B3 (bins 12..35), treble = C4..B6 (bins 36..71)
        def fold(block):
            return np.array([block[i::12].sum(axis=0) for i in range(12)])
        bass, treble = fold(C[12:36]), fold(C[36:72])
        bass /= bass.sum(axis=0, keepdims=True) + 1e-9
        treble /= treble.sum(axis=0, keepdims=True) + 1e-9
        return ks_from_chroma(bass_weight * bass + (1 - bass_weight) * treble)
    return f


# ---- current project detector (learned model fused with bgate) ------------------------------
def bpmkey_current(path: str):
    from bpmkey import keymodel
    import essentia.standard as es
    from bpmkey.analyze import _name_to_index
    y = _trim(load(path))
    bk, bs, _ = es.KeyExtractor(profileType="bgate")(y)
    ym = load(path, keymodel.SR)
    scores = keymodel.fuse(keymodel.log_probs(ym), _name_to_index(bk, bs))
    name, mode = keymodel.index_to_key(int(np.argmax(scores)))
    return _norm(name, mode)


def registry() -> dict:
    r = {"M1 KS librosa chroma_cqt": m1_ks("cqt"), "M1 KS librosa chroma_stft": m1_ks("stft")}
    for p in ("krumhansl", "temperley", "shaath", "bgate"):
        r[f"M2 Essentia KeyExtractor {p}"] = key_extractor(p)
    for p in ("edma", "edmm", "braw"):
        r[f"M3 Essentia KeyExtractor {p}"] = key_extractor(p)
    for p in ("edma", "bgate"):
        r[f"M4 HPCP36 {p}"] = hpcp36(p)
        r[f"M4 HPCP36 {p} no-detune"] = hpcp36(p, detune=False)
    r["M4 HPCP36 edma majmin"] = hpcp36("edma", majmin=True)
    for m in (4, 8):
        r[f"M7 HPSS(margin={m}) + edma"] = key_extractor("edma", harmonic=m)
        r[f"M7 HPSS(margin={m}) + bgate"] = key_extractor("bgate", harmonic=m)
    for w in (0.3, 0.5, 0.7):
        r[f"M9 bass/treble chroma w={w}"] = bass_treble(w)
    r["bpmkey current (learned+bgate)"] = bpmkey_current
    return r


NOT_RUN = {
    "M5 Faraldo multi-profile (edmkey)": "repo not vendored; Essentia edma+majmin (M4) approximates it",
    "M6 libKeyFinder": "no pip bindings / keyfinder-cli installed",
    "M8 Demucs stems + best": "demucs not installed (heavy torch download); not run",
    "M10 Key-CNN": "key-cnn/tensorflow not installed; not run",
    "M11 madmom CNN": "madmom does not install on Python 3.10/numpy 2; not run",
}
