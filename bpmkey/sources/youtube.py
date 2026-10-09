from __future__ import annotations

from ..matching import dynamic_threshold, score_candidate
from ..models import AudioSource, Track
from .base import MIN_SCORE, SourceFinder


class YouTube(SourceFinder):
    """Videos linked on the Discogs page first, then a YouTube search."""

    name = "youtube"

    def __init__(self, discogs_videos: list[dict] | None = None, search: bool = True,
                 track_titles: list[str] | None = None):
        self.videos = discogs_videos or []
        # Videos are linked by the release itself, so the artist often differs ("L.P.C" vs
        # "Lucky People Center") and the bar depends on how alike the release's titles are.
        self.video_threshold = dynamic_threshold(track_titles or [])
        self.search = search

    def _from_discogs(self, track: Track) -> list[AudioSource]:
        out = []
        for v in self.videos:
            sc = score_candidate(track.artist, track.title, track.duration,
                                 v.get("title", ""), "", v.get("duration"))
            if sc >= self.video_threshold:
                out.append(AudioSource("youtube", v["uri"], v.get("duration"), sc))
        # Follow the most similar linked video; keep others only if they are about as good
        best = max((s.match_score for s in out), default=0.0)
        return [s for s in out if s.match_score >= best - 0.05]

    def _from_search(self, track: Track) -> list[AudioSource]:
        import yt_dlp

        opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "noprogress": True}
        q = f"ytsearch5:{track.artist} {track.title}"
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(q, download=False)
        except yt_dlp.utils.YoutubeDLError:
            return []
        out = []
        for e in (info or {}).get("entries", []) or []:
            if not e:
                continue
            sc = score_candidate(track.artist, track.title, track.duration, e.get("title", ""),
                                 e.get("channel") or e.get("uploader") or "", e.get("duration"))
            if sc >= MIN_SCORE:
                out.append(AudioSource("youtube", e.get("url") or e.get("webpage_url"),
                                       e.get("duration"), sc))
        return out

    def find(self, track: Track) -> list[AudioSource]:
        found = self._from_discogs(track)
        if not found and self.search:
            found = self._from_search(track)
        return sorted(found, key=lambda s: -s.match_score)
