from __future__ import annotations

from ..lookup.base import get_json
from ..matching import score_candidate
from ..models import AudioSource, Track
from .base import MIN_SCORE, SourceFinder


class ITunes(SourceFinder):
    """Official 30-second previews from the iTunes Search API."""

    name = "itunes"

    def find(self, track: Track) -> list[AudioSource]:
        data = get_json("https://itunes.apple.com/search", params={
            "term": f"{track.artist} {track.title}", "entity": "song", "limit": 10})
        out = []
        for r in (data.get("results") if isinstance(data, dict) else None) or []:
            if not r.get("previewUrl"):
                continue
            dur = round(r["trackTimeMillis"] / 1000) if r.get("trackTimeMillis") else None
            sc = score_candidate(track.artist, track.title, track.duration,
                                 r.get("trackName", ""), r.get("artistName", ""), dur)
            if sc >= MIN_SCORE:
                out.append(AudioSource("itunes", r["previewUrl"], dur, sc))
        return sorted(out, key=lambda s: -s.match_score)
