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
