from .bandcamp import Bandcamp
from .itunes import ITunes
from .soundcloud import SoundCloud
from .youtube import YouTube


def finders_for(release: dict | None = None, discogs=None):
    """Full-length audio first (YouTube, Bandcamp, SoundCloud); 30 s iTunes preview last."""
    release = release or {}
    titles = [t["title"] for t in release.get("tracklist", []) if t.get("type_", "track") == "track"]
    return [YouTube(release.get("videos"), track_titles=titles), Bandcamp(release, discogs), SoundCloud(), ITunes()]
