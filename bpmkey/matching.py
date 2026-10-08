from __future__ import annotations

import re
from difflib import SequenceMatcher


def norm(s: str) -> str:
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s.lower())
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def is_match(artist: str, title: str, c_artist: str, c_title: str, threshold: float = 0.8) -> bool:
    return similarity(artist, c_artist) >= threshold and similarity(title, c_title) >= threshold


def token_containment(needle: str, hay: str) -> float:
    """Fraction of needle's tokens that appear in hay (order-insensitive)."""
    n, h = set(norm(needle).split()), set(norm(hay).split())
    return len(n & h) / len(n) if n else 0.0


_VERSION_WORDS = {"remix", "live", "cover", "mix", "edit", "instrumental", "acapella", "karaoke", "reprise"}


def version_penalty(track_title: str, cand_title: str) -> float:
    """Penalty when the candidate is a different version (remix/live/...) than the track."""
    # Keep bracketed text here: "(Remix)" is exactly what we're looking for
    t = set(re.findall(r"[a-z0-9]+", track_title.lower()))
    c = set(re.findall(r"[a-z0-9]+", cand_title.lower()))
    return 0.4 if (c & _VERSION_WORDS) - t else 0.0


DURATION_TOLERANCE = 6  # seconds
MAX_UNKNOWN_DURATION = 15 * 60


def score_candidate(artist: str, title: str, duration, c_title: str, c_extra: str = "",
                    c_duration=None) -> float:
    """0..1 match score; 0 when the duration is clearly wrong."""
    if duration and c_duration and abs(duration - c_duration) > DURATION_TOLERANCE:
        return 0.0
    if not duration and c_duration and c_duration > MAX_UNKNOWN_DURATION:
        return 0.0  # no reference length: reject DJ mixes / full albums
    hay = f"{c_title} {c_extra}"
    s = 0.65 * token_containment(title, hay) + 0.35 * token_containment(artist, hay)
    return max(0.0, s - version_penalty(title, c_title))
