from __future__ import annotations

import argparse

from .lookup import PROVIDERS
from .models import Track
from .reconcile import reconcile


def lookup_track(track: Track):
    for p in PROVIDERS:
        m = p.query(track)
        if m:
            track.measurements.append(m)
    return reconcile(track)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("artist")
    ap.add_argument("title")
    a = ap.parse_args()
    t = Track(0, "", a.artist, a.title)
    r = lookup_track(t)
    for m in t.measurements:
        print(f"  {m.origin:15} bpm={m.bpm} key={m.camelot} ({m.raw_key})")
    print(f"=> bpm={r.bpm} key={r.camelot} status={r.status}")


if __name__ == "__main__":
    main()
