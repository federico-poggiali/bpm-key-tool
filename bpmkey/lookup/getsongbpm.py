from __future__ import annotations

from .. import config
from ..camelot import to_camelot
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
        if not isinstance(hits, list) or not hits:
            return None
        h = hits[0]
        try:
            bpm = float(h.get("tempo"))
        except (TypeError, ValueError):
            bpm = None
        cam = to_camelot(h.get("open_key")) or to_camelot(h.get("key_of"))
        if bpm is None and cam is None:
            return None
        return Measurement(self.name, bpm or None, cam, h.get("key_of"))
