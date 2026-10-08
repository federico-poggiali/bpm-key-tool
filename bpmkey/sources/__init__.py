from .bandcamp import Bandcamp
from .itunes import ITunes
from .youtube import YouTube


def finders_for(discogs_videos=None):
    """Priority order: YouTube, Bandcamp (known URLs only), Apple preview."""
    return [YouTube(discogs_videos), Bandcamp(), ITunes()]
