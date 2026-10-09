from __future__ import annotations

from ..models import AudioSource, Track

MIN_SCORE = 0.75


class SourceFinder:
    name = "base"
    threshold = MIN_SCORE  # minimum match score; finders_for() sets it per release

    def find(self, track: Track) -> list[AudioSource]:  # best first
        raise NotImplementedError
