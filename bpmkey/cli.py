from __future__ import annotations

import argparse

from .discogs import DiscogsClient


def fmt_dur(s):
    return f"{s // 60}:{s % 60:02d}" if s else "--:--"


def main() -> None:
    ap = argparse.ArgumentParser(description="Discogs release -> BPM + Camelot key")
    ap.add_argument("url", help="Discogs release or master URL")
    args = ap.parse_args()

    release, tracks, videos = DiscogsClient().tracks(args.url)
    print(f"{release.get('title')}  ({release.get('year', '?')})  "
          f"[{len(tracks)} tracks, {len(videos)} videos]\n")
    for t in tracks:
        print(f"{t.position:>4}  {fmt_dur(t.duration)}  {t.artist} - {t.title}")


if __name__ == "__main__":
    main()
