"""Discogs API client and release mapping. URL/tracklist parsing is shared with bpmkey."""
import time
from collections.abc import Callable

import httpx
from bpmkey.discogs import _join_artists, parse_tracklist, parse_url

from app import config

API = "https://api.discogs.com"


class DiscogsError(Exception):
    pass


class DiscogsNotFound(DiscogsError):
    pass


class DiscogsClient:
    def __init__(self, token: str, client: httpx.Client | None = None,
                 sleep: Callable[[float], None] = time.sleep, max_retries: int = 5):
        if not token:
            raise DiscogsError("DISCOGS_TOKEN is not set (see .env)")
        self._http = client or httpx.Client(timeout=20)
        self._headers = {"User-Agent": config.USER_AGENT, "Authorization": f"Discogs token={token}"}
        self._sleep = sleep
        self._max_retries = max_retries

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            resp = self._http.request(method, f"{API}{path}", headers=self._headers, **kwargs)
            if resp.status_code == 429 and attempt < self._max_retries:
                retry_after = resp.headers.get("Retry-After")
                self._sleep(float(retry_after) if retry_after else min(2 ** attempt * 2, 60))
                continue
            if resp.status_code == 404:
                raise DiscogsNotFound(f"not found on Discogs: {path}")
            if resp.status_code == 429:
                raise DiscogsError("Discogs rate limit: gave up after retries")
            if resp.status_code >= 400:
                raise DiscogsError(f"Discogs returned {resp.status_code} for {path}")
            return resp
        raise DiscogsError("unreachable")

    def release(self, release_id: int) -> dict:
        return self._request("GET", f"/releases/{release_id}").json()

    def master_main_release(self, master_id: int) -> int:
        return self._request("GET", f"/masters/{master_id}").json()["main_release"]

    def resolve(self, url: str) -> tuple[int, int | None]:
        """Return (release_id, master_id); master_id is set when the URL was a master."""
        try:
            kind, id_ = parse_url(url)
        except ValueError as exc:
            raise DiscogsError(str(exc)) from exc
        if kind == "master":
            return self.master_main_release(id_), id_
        return id_, None


def _format_text(formats: list[dict]) -> str | None:
    if not formats:
        return None
    first = formats[0]
    parts = [first.get("name", "")]
    if first.get("qty") not in (None, "1"):
        parts[0] = f"{first['qty']}x{parts[0]}"
    parts += first.get("descriptions", [])
    return ", ".join(p for p in parts if p) or None


def release_to_record(data: dict) -> dict:
    images = data.get("images") or []
    labels = data.get("labels") or []
    return {
        "discogs_release_id": data["id"],
        "artist": _join_artists(data.get("artists", [])) or "Unknown artist",
        "title": data["title"],
        "label": labels[0]["name"] if labels else None,
        "year": data.get("year") or None,
        "format": _format_text(data.get("formats", [])),
        "cover_url": (images[0].get("uri") or images[0].get("uri150")) if images else None,
    }


def release_to_tracks(data: dict) -> list[dict]:
    return [
        {"position": t.position, "artist": t.artist, "title": t.title, "duration_sec": t.duration}
        for t in parse_tracklist(data, data["id"])
    ]
