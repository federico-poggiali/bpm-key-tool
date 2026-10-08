from __future__ import annotations

import html
import json
import re

from ..lookup.base import session
from ..matching import score_candidate
from ..models import AudioSource, Track
from .base import MIN_SCORE, SourceFinder

_RESULT = re.compile(r'<li class="searchresult[^"]*">(.*?)</li>', re.S)
_HREF = re.compile(r'<div class="heading">\s*<a href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', re.S)
_BY = re.compile(r'by\s+([^<\n]+)')
_TRALBUM = re.compile(r'data-tralbum="([^"]+)"')


def _text(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()


class Bandcamp(SourceFinder):
    """Stream URL from a Bandcamp track page's data-tralbum JSON.

    Bandcamp's search page now sits behind a JS bot challenge, so searching is off by
    default. `find` works for tracks whose Bandcamp URL is already known.
    """

    name = "bandcamp"

    def __init__(self, urls: dict[str, str] | None = None, search: bool = False):
        self.urls = urls or {}  # track position -> bandcamp track page URL
        self.search = search

    def _get(self, url: str, **kw) -> str | None:
        try:
            r = session.get(url, timeout=15, **kw)
            r.raise_for_status()
            return r.text
        except Exception:
            return None

    def find(self, track: Track) -> list[AudioSource]:
        if track.position in self.urls:
            src = self._stream(self.urls[track.position], track)
            return [src] if src else []
        if not self.search:
            return []
        page = self._get("https://bandcamp.com/search",
                         params={"q": f"{track.artist} {track.title}", "item_type": "t"})
        if not page:
            return []
        out: list[AudioSource] = []
        for block in _RESULT.findall(page)[:5]:
            m = _HREF.search(block)
            if not m:
                continue
            url, title = m.group(1).split("?")[0], _text(m.group(2))
            by = _BY.search(_text(block))
            if score_candidate(track.artist, track.title, None, title, by.group(1) if by else "") < MIN_SCORE:
                continue
            src = self._stream(url, track)
            if src:
                out.append(src)
        return sorted(out, key=lambda s: -s.match_score)

    def _stream(self, page_url: str, track: Track) -> AudioSource | None:
        page = self._get(page_url)
        m = _TRALBUM.search(page or "")
        if not m:
            return None
        try:
            info = json.loads(html.unescape(m.group(1)))["trackinfo"][0]
            mp3 = (info.get("file") or {}).get("mp3-128")
        except (ValueError, KeyError, IndexError):
            return None
        if not mp3:
            return None
        dur = round(info["duration"]) if info.get("duration") else None
        sc = score_candidate(track.artist, track.title, track.duration,
                             info.get("title", ""), page_url, dur)
        return AudioSource("bandcamp", mp3, dur, max(sc, 0.0)) if sc >= MIN_SCORE else None
