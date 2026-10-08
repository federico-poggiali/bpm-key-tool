from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AudioSource:
    kind: str  # youtube | bandcamp | itunes
    url: str
    duration: Optional[int] = None  # seconds
    match_score: float = 0.0


@dataclass
class Measurement:
    origin: str  # getsongbpm | deezer | acousticbrainz | essentia
    bpm: Optional[float] = None
    camelot: Optional[str] = None
    raw_key: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class Track:
    release_id: int
    position: str
    artist: str
    title: str
    duration: Optional[int] = None  # seconds
    audio_sources: list[AudioSource] = field(default_factory=list)
    measurements: list[Measurement] = field(default_factory=list)


@dataclass
class Result:
    track: Track
    bpm: Optional[float] = None
    camelot: Optional[str] = None
    status: str = "none"  # agreed | single | conflict | analyzed | none
    note: str = ""
