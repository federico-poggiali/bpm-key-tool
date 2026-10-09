# bpm-key-tool

A personal tool that takes a [Discogs](https://www.discogs.com) release link and returns the **BPM** and **musical key (Camelot notation)** for every track.

It looks values up online first, compares the sources, and only analyses the audio when the online results are missing or disagree.

## Status

- [x] Discogs release URL → tracklist and YouTube videos
- [x] Audio sources: Discogs videos → YouTube search → iTunes 30 s preview (Bandcamp for known URLs only; its search is behind a bot challenge)
- [x] Online BPM/key lookup: GetSongBPM, Deezer, AcousticBrainz
- [x] Audio analysis fallback: yt-dlp + Essentia (BPM, EDM key profile)
- [x] Camelot conversion, reconciliation, SQLite cache, CSV export

## Usage

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your Discogs token, GetSongBPM key and contact email
python -m bpmkey https://www.discogs.com/release/10296528        # command line
python -m bpmkey.server                                           # local web UI on http://127.0.0.1:8765
```

CLI options: `--no-analyze` (online lookups only), `--refresh` (redo online lookups, keep cached audio analysis), `--reanalyze` (redo everything), `--csv out.csv`, `--tracks-only`, `-v`.
The web UI also accepts `?url=<discogs link>` to start straight away.

Tracks are marked `agreed` when sources agree, `analyzed` when the audio analysis overruled or replaced the online values, `single` when only one source answered, and `conflict`/`none` otherwise.

## How it works

1. Look the track up in GetSongBPM, Deezer and AcousticBrainz. Every hit is checked against the artist and title, because these APIs happily return unrelated songs (and remixes of the right one).
2. If BPM and key are confirmed by at least two sources, stop.
3. Otherwise find the audio (Discogs videos, YouTube search, Bandcamp via artist/label pages, SoundCloud, iTunes preview as a last resort), matched by title and duration, and analyze it.
4. Audio gives a BPM and a probability for each of the 24 keys. Validated database keys then add weight to their key, so a close audio call can be tipped by an independent source, but a confident one can't.

## Accuracy

Measured against human-labelled electronic music (Beatport previews; audio not included in this repo):

| | result |
|---|---|
| BPM, within ±4% of the Beatport BPM (GiantSteps-MTG, 885 clips) | 94.8% |
| Key, exact match, Essentia `edmm` profile, the shipped detector (GiantSteps Key, 604 clips) | 65% (weighted MIREX score 0.70) |
| Key, exact match, Essentia `bgate` profile, the backup (same clips) | 61% (0.68) |
| Key, exact match, Essentia `edma` profile (same clips) | 58% (0.65) |
| Key, exact match, classical Krumhansl profile (same clips) | 49% (0.59) |

Key detection uses `edmm`, with `bgate` as backup if `edmm` fails. When `edmm` is unsure (about 1 clip in 5, where it is right only about a third of the time) its confidence is lowered, so the database votes can outvote it. Switching to `bgate` in that case did not help on GiantSteps. The benchmark scripts and reports are in `benchmark/` (`report_giantsteps.md`, `segments_report.md`).

Key detection by audio alone is the weak spot, so the database votes matter. A 90% exact-key target is not realistic for any current method.

## Known limitations

- Half/double tempo is ambiguous for some genres (e.g. footwork at 80 vs 160 BPM).
- Key detection is unreliable on atonal or heavily percussive music, and on tracks that change key.
- YouTube sometimes blocks downloads (403 or age-gating); the next source is tried automatically.
- Bandcamp's own search is behind a bot challenge, so tracks are only found through artist and label pages, with rate limiting.

## Data sources and credits

- BPM and key data provided by [GetSongBPM](https://getsongbpm.com).
- Release metadata from the [Discogs API](https://www.discogs.com/developers).
- Additional BPM data from [Deezer](https://developers.deezer.com) and [AcousticBrainz](https://acousticbrainz.org) via [MusicBrainz](https://musicbrainz.org).

This is a personal project and is not affiliated with any of the services above.
