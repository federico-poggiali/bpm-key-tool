from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

from . import keymodel
from .camelot import key_index_to_camelot
from .models import Measurement

SAMPLE_RATE = 44100
MAX_ANALYSIS_SECONDS = 8 * 60  # a single short slice can land on a modulation
MAX_VIDEO_SECONDS = 20 * 60  # skip DJ mixes / full albums
BPM_RANGE = (70.0, 180.0)


class AudioUnavailable(Exception):
    """Source could not be downloaded (age-gated, removed, geo-blocked, too long...)."""


def clamp_bpm(bpm: float, lo: float = BPM_RANGE[0], hi: float = BPM_RANGE[1]) -> float:
    """Fold half/double-tempo errors into a sensible range."""
    while bpm < lo:
        bpm *= 2
    while bpm > hi:
        bpm /= 2
    return bpm


def download_audio(url: str, dest: Path) -> Path:
    """Download the native audio stream (no ffmpeg needed). `url` may be 'ytsearch1:...'."""
    import yt_dlp

    opts = {
        "format": "bestaudio",
        "outtmpl": str(dest / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "match_filter": yt_dlp.utils.match_filter_func(f"duration<={MAX_VIDEO_SECONDS}"),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info and "entries" in info:
                info = next((e for e in info["entries"] if e), None)
            if not info:
                raise AudioUnavailable("nothing found (or filtered by length)")
            path = Path(ydl.prepare_filename(info))
    except yt_dlp.utils.YoutubeDLError as e:
        raise AudioUnavailable(str(e).splitlines()[0][:200]) from e
    if not path.exists():
        raise AudioUnavailable("download failed or was filtered out")
    return path


def analyze_file(path: Path | str) -> Measurement:
    """BPM from the whole track; key from sparse excerpts plus an Essentia vote."""
    import essentia.standard as es

    audio = es.MonoLoader(filename=str(path), sampleRate=SAMPLE_RATE)()
    n = MAX_ANALYSIS_SECONDS * SAMPLE_RATE
    if len(audio) > n:
        start = (len(audio) - n) // 2
        audio = audio[start:start + n]

    bpm, _, _, _, _ = es.RhythmExtractor2013(method="multifeature")(audio)
    bpm = clamp_bpm(float(bpm))

    bkey, bscale, _ = es.KeyExtractor(profileType="bgate")(audio)
    bgate_idx = _name_to_index(bkey, bscale)
    try:
        y = es.MonoLoader(filename=str(path), sampleRate=keymodel.SR)()
        scores = keymodel.fuse(keymodel.log_probs(y), bgate_idx)
    except ImportError:  # librosa/scipy missing: fall back to the Essentia vote alone
        scores = np.full(24, -10.0)
        scores[bgate_idx] = 0.0
    best = int(np.argmax(scores))
    name, mode = keymodel.index_to_key(best)
    return Measurement("essentia", round(bpm, 1), key_index_to_camelot(best), f"{name} {mode}",
                       round(float(np.exp(scores[best])), 2), [round(float(v), 3) for v in scores])


def _name_to_index(key: str, scale: str) -> int:
    pc = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
          "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}[key]
    return pc + (12 if scale == "minor" else 0)


def analyze_url(url: str) -> Measurement:
    """Download -> analyze -> delete. Works for YouTube URLs, other yt-dlp sites, or ytsearch1:."""
    with tempfile.TemporaryDirectory(prefix="bpmkey_") as tmp:
        return analyze_file(download_audio(url, Path(tmp)))


def download_direct(url: str, dest: Path) -> Path:
    """Plain HTTP download for direct media URLs (Bandcamp streams, iTunes previews)."""
    import requests

    ext = Path(url.split("?")[0]).suffix or ".mp3"
    path = dest / f"audio{ext}"
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
    except requests.RequestException as e:
        raise AudioUnavailable(str(e)[:200]) from e
    return path


def analyze_source(source) -> Measurement:
    """Analyze an AudioSource of any kind; temp files are always removed."""
    with tempfile.TemporaryDirectory(prefix="bpmkey_") as tmp:
        d = Path(tmp)
        # yt-dlp handles page URLs (YouTube, Bandcamp, SoundCloud); iTunes gives a raw preview file
        path = download_direct(source.url, d) if source.kind == "itunes" else download_audio(source.url, d)
        m = analyze_file(path)
        m.origin = f"essentia:{source.kind}"
        return m
