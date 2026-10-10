from ..matching import dynamic_threshold
from .itunes import ITunes
from .soundcloud import SoundCloud
from .youtube import YouTube


def finders_for(release: dict | None = None):
    """Full-length audio first (YouTube, SoundCloud); 30 s iTunes preview last."""
    release = release or {}
    titles = [t["title"] for t in release.get("tracklist", []) if t.get("type_", "track") == "track"]
    soundcloud = SoundCloud()
    soundcloud.threshold = dynamic_threshold(titles)  # same bar as YouTube
    return [YouTube(release.get("videos"), track_titles=titles), soundcloud, ITunes()]
