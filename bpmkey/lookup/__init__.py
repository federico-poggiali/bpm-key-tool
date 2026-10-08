from .acousticbrainz import AcousticBrainz
from .deezer import Deezer
from .getsongbpm import GetSongBPM

PROVIDERS = [GetSongBPM(), Deezer(), AcousticBrainz()]
