from __future__ import annotations

import re
import time
from typing import Optional

import requests

from . import config
from .models import Track

API = "https://api.discogs.com"
_RELEASE_RE = re.compile(r"/(release|master)/(\d+)")


def parse_url(url: str) -> tuple[str, int]:
    """Return ('release'|'master', id) from a Discogs URL."""
    m = _RELEASE_RE.search(url)
    if not m:
        raise ValueError(f"Not a Discogs release/master URL: {url}")
    return m.group(1), int(m.group(2))


def parse_duration(s: str) -> Optional[int]:
    """'5:32' -> 332, '1:02:03' -> 3723, '' -> None."""
    if not s:
        return None
    parts = s.strip().split(":")
    if not all(p.isdigit() for p in parts) or len(parts) > 3:
        return None
    secs = 0
    for p in parts:
        secs = secs * 60 + int(p)
    return secs


def _clean_artist(name: str) -> str:
    # Discogs disambiguates duplicate names as "Name (2)"
    return re.sub(r"\s*\(\d+\)$", "", name).strip()


def _join_artists(artists: list[dict]) -> str:
    out = []
    for a in artists:
        out.append(_clean_artist(a.get("anv") or a["name"]))
        out.append(f" {a['join']} " if a.get("join") and a["join"] != "," else ", ")
    text = "".join(out).rstrip(", ").strip()
    return text


class DiscogsClient:
    def __init__(self, token: str = config.DISCOGS_TOKEN):
        if not token:
            raise RuntimeError("DISCOGS_TOKEN is not set (see .env)")
        self.s = requests.Session()
        self.s.headers.update(
            {"User-Agent": config.USER_AGENT, "Authorization": f"Discogs token={token}"}
        )

    def _get(self, path: str) -> dict:
        for attempt in range(3):
            r = self.s.get(f"{API}{path}", timeout=20)
            if r.status_code == 429:  # rate limited (60/min)
                time.sleep(2 ** attempt * 5)
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("Discogs rate limit: gave up after retries")

    def release(self, release_id: int) -> dict:
        return self._get(f"/releases/{release_id}")

    def resolve(self, url: str) -> int:
        kind, id_ = parse_url(url)
        if kind == "master":
            return self._get(f"/masters/{id_}")["main_release"]
        return id_

    def tracks(self, url: str) -> tuple[dict, list[Track], list[dict]]:
        """Return (release_json, tracks, videos)."""
        rid = self.resolve(url)
        data = self.release(rid)
        return data, parse_tracklist(data, rid), data.get("videos", [])


def parse_tracklist(data: dict, release_id: int) -> list[Track]:
    release_artist = _join_artists(data.get("artists", []))
    tracks: list[Track] = []

    def add(t: dict, parent_artist: str) -> None:
        artists = t.get("artists")
        artist = _join_artists(artists) if artists else parent_artist
        tracks.append(
            Track(
                release_id=release_id,
                position=t.get("position", ""),
                artist=artist,
                title=t["title"].strip(),
                duration=parse_duration(t.get("duration", "")),
            )
        )

    for t in data.get("tracklist", []):
        kind = t.get("type_", "track")
        if kind == "track":
            add(t, release_artist)
        elif kind == "index":  # track group with sub_tracks
            for sub in t.get("sub_tracks", []):
                add(sub, release_artist)
        # 'heading' entries are skipped
    return tracks
