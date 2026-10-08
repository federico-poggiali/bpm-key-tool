from __future__ import annotations

import time

from ..camelot import to_camelot
from ..matching import is_match
from ..models import Measurement, Track
from .base import Lookup, get_json

MB = "https://musicbrainz.org/ws/2"
AB = "https://acousticbrainz.org/api/v1"
_last_mb = 0.0


def _mb_get(url: str, **kw):
    """MusicBrainz allows ~1 request/second."""
    global _last_mb
    wait = 1.1 - (time.monotonic() - _last_mb)
    if wait > 0:
        time.sleep(wait)
    _last_mb = time.monotonic()
    return get_json(url, **kw)


def _key(tonal: dict):
    # Prefer the EDM profile; fall back to the generic one
    for prefix in ("key_edma", "key_krumhansl"):
        k = tonal.get(prefix)
        if isinstance(k, dict) and k.get("key"):
            return k["key"], k.get("scale")
    if tonal.get("key_key"):
        return tonal["key_key"], tonal.get("key_scale")
    return None


class AcousticBrainz(Lookup):
    name = "acousticbrainz"

    def _mbids(self, track: Track) -> list[str]:
        q = f'recording:"{track.title}" AND artist:"{track.artist}"'
        res = _mb_get(f"{MB}/recording", params={"query": q, "fmt": "json", "limit": 5})
        recs = res.get("recordings") if isinstance(res, dict) else None
        out = []
        for r in recs or []:
            credit = " ".join(c.get("name", "") for c in r.get("artist-credit", []))
            if is_match(track.artist, track.title, credit, r.get("title", "")):
                out.append(r["id"])
        return out[:3]

    def query(self, track: Track) -> Measurement | None:
        for mbid in self._mbids(track):
            data = get_json(f"{AB}/{mbid}/low-level")
            if not isinstance(data, dict):
                continue
            key = _key(data.get("tonal", {}))
            cam = to_camelot(key) if key else None
            bpm = data.get("rhythm", {}).get("bpm")
            if bpm or cam:
                raw = f"{key[0]} {key[1]}" if key else None
                return Measurement(self.name, float(bpm) if bpm else None, cam, raw)
        return None
