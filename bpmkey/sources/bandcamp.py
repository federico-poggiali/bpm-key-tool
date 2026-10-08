from __future__ import annotations

import json
import re
import time

from ..matching import MIN_ALBUM_SCORE, norm, score_candidate, similarity
from ..models import AudioSource, Track
from .base import MIN_SCORE, SourceFinder

_BC_HOST = re.compile(r"https?://([a-z0-9-]+)\.bandcamp\.com", re.I)
MAX_DOMAINS = 2
MAX_ALBUMS = 3
PAUSE = 1.5  # seconds between Bandcamp requests: be gentle


def _slug_guesses(name: str) -> list[str]:
    base = re.sub(r"[^a-z0-9 ]+", "", norm(name))
    return list(dict.fromkeys(g for g in (base.replace(" ", ""), base.replace(" ", "-")) if g))


def _ytdl(flat: bool):
    import yt_dlp

    return yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noprogress": True,
                             "extract_flat": flat, "playlistend": 40})


class Bandcamp(SourceFinder):
    """Full-length Bandcamp streams, found through the artist's or label's own page.

    Bandcamp's search sits behind a bot challenge, so instead we follow links Discogs
    already has (artist/label profiles, release notes), plus a name-based guess, and
    read the pages with yt-dlp's Bandcamp extractors.
    """

    name = "bandcamp"

    def __init__(self, release: dict | None = None, discogs=None):
        self.release = release or {}
        self.discogs = discogs
        self._domains: list[str] | None = None
        self._albums: dict[str, list[dict]] = {}
        self.blocked = False  # set on the first 429 / challenge: stop asking

    # --- discovery -------------------------------------------------------------------
    def domains(self, track: Track) -> list[str]:
        if self._domains is None:
            found = [m.lower() for m in _BC_HOST.findall(json.dumps(self.release))]
            for kind in ("labels", "artists"):
                for item in (self.release.get(kind) or [])[:3]:
                    try:
                        profile = self.discogs._get(item["resource_url"].replace("https://api.discogs.com", "")) if self.discogs else {}
                    except Exception:
                        continue
                    found += [m.lower() for u in profile.get("urls", []) for m in _BC_HOST.findall(u)]
            self._domains = list(dict.fromkeys(found))
        guesses = _slug_guesses(track.artist)
        return list(dict.fromkeys(self._domains + guesses))[:MAX_DOMAINS + 2]

    def _guard(self, e: Exception) -> None:
        if "429" in str(e) or "challenge" in str(e).lower():
            self.blocked = True

    def _list(self, domain: str) -> list[dict]:
        if domain not in self._albums:
            if self.blocked:
                return []
            time.sleep(PAUSE)
            try:
                with _ytdl(True) as y:
                    info = y.extract_info(f"https://{domain}.bandcamp.com/music", download=False)
                self._albums[domain] = [e for e in (info or {}).get("entries", []) if e and e.get("url")]
            except Exception as e:
                self._guard(e)
                self._albums[domain] = []
        return self._albums[domain]

    def _tracks_of(self, url: str) -> list[dict]:
        if self.blocked:
            return []
        time.sleep(PAUSE)
        try:
            with _ytdl(False) as y:
                info = y.extract_info(url, download=False)
        except Exception as e:
            self._guard(e)
            return []
        return (info or {}).get("entries") or [info] if info else []

    # --- matching --------------------------------------------------------------------
    def find(self, track: Track) -> list[AudioSource]:
        rel_title = self.release.get("title", "")
        out: list[AudioSource] = []
        for domain in self.domains(track):
            if self.blocked:
                break
            items = self._list(domain)
            if not items:
                continue
            # Albums whose slug resembles the Discogs release title come first
            def album_rank(e):
                slug = e["url"].rsplit("/", 1)[-1].replace("-", " ")
                return -max(similarity(rel_title, slug), similarity(track.title, slug))
            for e in sorted(items, key=album_rank)[:MAX_ALBUMS]:
                for t in self._tracks_of(e["url"]):
                    title = t.get("track") or t.get("title") or ""
                    sc = score_candidate(track.artist, track.title, track.duration,
                                         title, t.get("artist") or t.get("uploader") or track.artist,
                                         round(t["duration"]) if t.get("duration") else None)
                    url = t.get("webpage_url") or t.get("url")
                    if sc >= MIN_SCORE and url:
                        out.append(AudioSource("bandcamp", url, round(t["duration"]) if t.get("duration") else None, sc))
                if out:
                    return sorted(out, key=lambda s: -s.match_score)
        return sorted(out, key=lambda s: -s.match_score)
