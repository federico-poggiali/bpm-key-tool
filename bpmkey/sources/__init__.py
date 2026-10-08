from .bandcamp import Bandcamp
from .itunes import ITunes
from .soundcloud import SoundCloud
from .youtube import YouTube


def finders_for(release: dict | None = None, discogs=None):
    """Full-length audio first (YouTube, Bandcamp, SoundCloud); 30 s iTunes preview last."""
    release = release or {}
    return [YouTube(release.get("videos")), Bandcamp(release, discogs), SoundCloud(), ITunes()]
