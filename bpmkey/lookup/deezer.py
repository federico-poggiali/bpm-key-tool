from __future__ import annotations

from ..matching import is_match
from ..models import Measurement, Track
from .base import Lookup, get_json


class Deezer(Lookup):
    name = "deezer"
    API = "https://api.deezer.com"

    def query(self, track: Track) -> Measurement | None:
        res = get_json(f"{self.API}/search",
                       params={"q": f"{track.artist} {track.title}", "limit": 5})
        for item in (res.get("data") if isinstance(res, dict) else None) or []:
            if not is_match(track.artist, track.title,
                            item["artist"]["name"], item["title"]):
                continue
            detail = get_json(f"{self.API}/track/{item['id']}")
            bpm = detail.get("bpm") if isinstance(detail, dict) else None
            if bpm:  # Deezer reports 0 when unknown
                return Measurement(self.name, float(bpm))
        return None
