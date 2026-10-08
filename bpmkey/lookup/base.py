from __future__ import annotations

import requests

from .. import config
from ..models import Measurement, Track

session = requests.Session()
session.headers["User-Agent"] = config.USER_AGENT


def get_json(url: str, **kw):
    """GET returning parsed JSON, or None on any network/HTTP/parse failure."""
    try:
        r = session.get(url, timeout=15, **kw)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError):
        return None


class Lookup:
    name = "base"

    def query(self, track: Track) -> Measurement | None:  # pragma: no cover
        raise NotImplementedError
