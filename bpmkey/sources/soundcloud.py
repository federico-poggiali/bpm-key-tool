from __future__ import annotations

from ..matching import score_candidate
from ..models import AudioSource, Track
from .base import MIN_SCORE, SourceFinder


class SoundCloud(SourceFinder):
    """SoundCloud search via yt-dlp. Many underground labels upload there, not to YouTube."""

    name = "soundcloud"

    def find(self, track: Track) -> list[AudioSource]:
        import yt_dlp

        opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "noprogress": True}
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                info = y.extract_info(f"scsearch8:{track.artist} {track.title}", download=False)
        except yt_dlp.utils.YoutubeDLError:
            return []
        out = []
        for e in (info or {}).get("entries", []) or []:
            if not e or not e.get("url"):
                continue
            sc = score_candidate(track.artist, track.title, track.duration, e.get("title", ""),
                                 e.get("uploader") or "", e.get("duration"))
            if sc >= MIN_SCORE:
                out.append(AudioSource("soundcloud", e["url"], round(e["duration"]) if e.get("duration") else None, sc))
        return sorted(out, key=lambda s: -s.match_score)
