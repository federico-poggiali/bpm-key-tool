from __future__ import annotations

import argparse
import csv
import logging
import sys

from .discogs import DiscogsClient
from .pipeline import Pipeline


def fmt_dur(s):
    return f"{s // 60}:{s % 60:02d}" if s else "--:--"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="bpmkey", description="Discogs release -> BPM + Camelot key")
    ap.add_argument("url", help="Discogs release or master URL")
    ap.add_argument("--tracks-only", action="store_true", help="just list the tracklist")
    ap.add_argument("--no-analyze", action="store_true", help="online lookups only, skip audio analysis")
    ap.add_argument("--refresh", action="store_true", help="ignore cached lookups")
    ap.add_argument("--csv", metavar="FILE", help="also write results to a CSV file")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.ERROR, format="%(message)s")

    if args.tracks_only:
        release, tracks, videos = DiscogsClient().tracks(args.url)
        print(f"{release.get('title')}  ({release.get('year', '?')})  "
              f"[{len(tracks)} tracks, {len(videos)} videos]\n")
        for t in tracks:
            print(f"{t.position:>4}  {fmt_dur(t.duration)}  {t.artist} - {t.title}")
        return

    rows = []
    print(f"{'pos':>4}  {'BPM':>6}  {'key':>4}  {'status':<9}  track")
    for r in Pipeline(analyze=not args.no_analyze, refresh=args.refresh).run(args.url):
        t = r.track
        bpm = f"{r.bpm:.1f}" if r.bpm else "-"
        print(f"{t.position:>4}  {bpm:>6}  {r.camelot or '-':>4}  {r.status:<9}  "
              f"{t.artist} - {t.title}" + (f"   [{r.note}]" if r.note else ""))
        sys.stdout.flush()
        rows.append([t.position, t.artist, t.title, r.bpm or "", r.camelot or "", r.status, r.note])
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["position", "artist", "title", "bpm", "camelot", "status", "note"])
            w.writerows(rows)
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
