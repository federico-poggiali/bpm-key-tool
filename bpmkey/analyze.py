from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from .camelot import to_camelot
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
    """BPM + key from an audio file, using the whole track (centered, capped for very long files)."""
    import essentia.standard as es

    audio = es.MonoLoader(filename=str(path), sampleRate=SAMPLE_RATE)()
    n = MAX_ANALYSIS_SECONDS * SAMPLE_RATE
    if len(audio) > n:
        start = (len(audio) - n) // 2
        audio = audio[start:start + n]

    bpm, _, beat_conf, _, _ = es.RhythmExtractor2013(method="multifeature")(audio)
    bpm = clamp_bpm(float(bpm))

    key, scale, strength = es.KeyExtractor(profileType="edma")(audio)
    alt_key, alt_scale, _ = es.KeyExtractor(profileType="krumhansl")(audio)
    cam = to_camelot((key, scale))
    # Confidence: key strength, boosted when two profiles agree
    agree = to_camelot((alt_key, alt_scale)) == cam
    conf = round(min(1.0, float(strength) * (1.0 if agree else 0.7)), 2)
    return Measurement("essentia", round(bpm, 1), cam, f"{key} {scale}", conf)


def analyze_url(url: str) -> Measurement:
    """Download -> analyze -> delete. Works for YouTube URLs, other yt-dlp sites, or ytsearch1:."""
    with tempfile.TemporaryDirectory(prefix="bpmkey_") as tmp:
        return analyze_file(download_audio(url, Path(tmp)))
