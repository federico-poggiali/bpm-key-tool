from __future__ import annotations

import logging
from typing import Iterator

from .analyze import AudioUnavailable, analyze_source
from .cache import Cache
from .discogs import DiscogsClient
from .lookup import PROVIDERS
from .models import Result, Track
from .reconcile import finalize, is_analysis, needs_analysis, reconcile
from .sources import finders_for

log = logging.getLogger("bpmkey")
MAX_ATTEMPTS = 3  # audio sources tried per track before giving up


class Pipeline:
    def __init__(self, analyze: bool = True, refresh: bool = False, cache: Cache | None = None):
        self.analyze = analyze
        self.refresh = refresh
        self.cache = cache or Cache()

    def _lookup(self, track: Track) -> None:
        cached = None if self.refresh else self.cache.get(track)
        if cached is not None:
            track.measurements = cached
            return
        for p in PROVIDERS:
            try:
                m = p.query(track)
            except Exception as e:  # one broken provider must not kill the release
                log.warning("%s failed for %s: %s", p.name, track.title, e)
                continue
            if m:
                track.measurements.append(m)
        self.cache.put(track)

    def _analyze(self, track: Track, finders) -> str:
        """Try audio sources in priority order. Returns a note describing the outcome."""
        tried = 0
        for f in finders:
            try:
                sources = f.find(track)
            except Exception as e:
                log.warning("%s search failed: %s", f.name, e)
                continue
            for src in sources:
                if tried >= MAX_ATTEMPTS:
                    return "no usable audio source"
                tried += 1
                try:
                    track.measurements.append(analyze_source(src))
                    self.cache.put(track)
                    return ""
                except AudioUnavailable as e:
                    log.info("%s unavailable (%s): %s", f.name, src.url, e)
                except Exception as e:
                    log.warning("analysis failed on %s: %s", src.url, e)
        return "no audio source found" if tried == 0 else "no usable audio source"

    def run(self, url: str) -> Iterator[Result]:
        _, tracks, videos = DiscogsClient().tracks(url)
        finders = finders_for(videos)
        for track in tracks:
            self._lookup(track)
            result = reconcile(track)
            note = ""
            if self.analyze and needs_analysis(result) and not any(is_analysis(m) for m in track.measurements):
                note = self._analyze(track, finders)
            result = finalize(track)
            if note:
                result.note = "; ".join(x for x in (result.note, note) if x)
            yield result
