from __future__ import annotations

import re
from difflib import SequenceMatcher


def norm(s: str) -> str:
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s.lower())
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def is_match(artist: str, title: str, c_artist: str, c_title: str, threshold: float = 0.8) -> bool:
    """Same artist, same title, and not a different version (remix/live/...) of it."""
    return (similarity(artist, c_artist) >= threshold
            and similarity(title, c_title) >= threshold
            and version_penalty(title, c_title) == 0)


def token_containment(needle: str, hay: str) -> float:
    """Fraction of needle's tokens that appear in hay (order-insensitive)."""
    n, h = set(norm(needle).split()), set(norm(hay).split())
    return len(n & h) / len(n) if n else 0.0


_VERSION_WORDS = {"remix", "live", "cover", "mix", "instrumental", "acapella", "karaoke", "reprise", "dub"}
# Labels that don't change tempo or key
_HARMLESS = re.compile(r"original mix|original version|radio edit|radio mix|album version|single version|\bedit\b|\boriginal\b|\bremaster(ed)?( \d{4})?\b")


def version_penalty(track_title: str, cand_title: str) -> float:
    """Penalty when the candidate is a different version (remix/live/...) than the track."""
    # Keep bracketed text here: "(Remix)" is exactly what we're looking for
    t = set(re.findall(r"[a-z0-9]+", _HARMLESS.sub(" ", track_title.lower())))
    c = set(re.findall(r"[a-z0-9]+", _HARMLESS.sub(" ", cand_title.lower())))
    return 0.4 if (c & _VERSION_WORDS) - t else 0.0


BRACKET_WEIGHT = 0.2  # score lost when none of the track's bracketed words appear in the candidate


def bracket_text(title: str) -> str:
    """Everything inside (...) or [...], e.g. 'Da Falcon Mix' for 'Rodney King (Da Falcon Mix)'."""
    return " ".join(x or y for x, y in re.findall(r"\((.*?)\)|\[(.*?)\]", title))


# Video descriptors, not part of the song's version: "(Full Video)", "[Official Lyrics Video]", ...
_VIDEO_NOISE = re.compile(
    r"\b(official|full|lyrics?|music|video|audio|clip|visuali[sz]er|hd|hq|4k|1080p|720p|"
    r"from|mtv|minutes?|\d+)\b")


def bracket_penalty(track_title: str, cand_title: str) -> float:
    """Penalty when the candidate labels itself as a different version than the track.

    Compares the track's bracketed words (mix/remix name) with the candidate's, scaled by
    the share missing. Video descriptors in the candidate's brackets are ignored, and a
    candidate left with no version label says nothing either way, so is not penalised."""
    tokens = set(re.findall(r"[a-z0-9]+", _HARMLESS.sub(" ", bracket_text(track_title).lower())))
    cand_label = _VIDEO_NOISE.sub(" ", bracket_text(cand_title).lower())
    cand = set(re.findall(r"[a-z0-9]+", cand_label))
    if not tokens or not cand:
        return 0.0
    return BRACKET_WEIGHT * (1 - len(tokens & cand) / len(tokens))


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
    return max(0.0, s - version_penalty(title, c_title) - bracket_penalty(title, c_title))


MIN_ALBUM_SCORE = 0.6


# Dynamic threshold for videos linked on the Discogs release itself.
# When the release's titles are all alike (one song in several mixes) a video is easy to pair
# with the wrong track, so demand a near-exact match; when the titles are unrelated, any
# video that fits one title is safe to accept.
DISCOGS_MIN_THRESHOLD = 0.55
DISCOGS_MAX_THRESHOLD = 0.95
SIMILAR_TITLES = 0.75  # mean title similarity at or above which the strict threshold applies


def title_similarity(titles: list[str]) -> float:
    """Mean pairwise similarity (0..1) of the release's track titles."""
    pairs = [(a, b) for i, a in enumerate(titles) for b in titles[i + 1:]]
    return sum(similarity(a, b) for a, b in pairs) / len(pairs) if pairs else 0.0


def dynamic_threshold(titles: list[str]) -> float:
    """55% for unrelated titles rising linearly to 95% once they are 75% similar."""
    ramp = min(1.0, title_similarity(titles) / SIMILAR_TITLES)
    return DISCOGS_MIN_THRESHOLD + (DISCOGS_MAX_THRESHOLD - DISCOGS_MIN_THRESHOLD) * ramp
