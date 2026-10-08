from __future__ import annotations

from .. import config
from ..camelot import open_key_to_camelot, to_camelot
from ..matching import is_match
from ..models import Measurement, Track
from .base import Lookup, get_json


class GetSongBPM(Lookup):
    name = "getsongbpm"
    URL = "https://api.getsong.co/search/"

    def query(self, track: Track) -> Measurement | None:
        if not config.GETSONGBPM_KEY:
            return None
        data = get_json(self.URL, params={
            "api_key": config.GETSONGBPM_KEY, "type": "both",
            "lookup": f"song:{track.title} artist:{track.artist}",
        })
        hits = data.get("search") if isinstance(data, dict) else None
        if not isinstance(hits, list):
            return None
        # The API fuzzy-matches and happily returns unrelated songs: verify every hit
        for h in hits:
            if not is_match(track.artist, track.title,
                            (h.get("artist") or {}).get("name", ""), h.get("title", "")):
                continue
            try:
                bpm = float(h.get("tempo"))
            except (TypeError, ValueError):
                bpm = None
            cam = open_key_to_camelot(h.get("open_key")) or to_camelot(h.get("key_of"))
            if bpm or cam:
                return Measurement(self.name, bpm or None, cam, h.get("key_of"))
        return None
