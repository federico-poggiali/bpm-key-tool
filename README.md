# bpm-key-tool

A personal tool that takes a [Discogs](https://www.discogs.com) release link and returns the **BPM** and **musical key (Camelot notation)** for every track.

It looks values up online first, compares the sources, and only analyses the audio when the online results are missing or disagree.

## Status

- [x] Discogs release URL → tracklist and YouTube videos
- [x] Audio sources: Discogs videos → YouTube search → SoundCloud → iTunes 30 s preview
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
3. Otherwise find the audio (Discogs videos, YouTube search, SoundCloud, iTunes preview as a last resort), matched by title and duration, and analyze it.
4. Audio gives a BPM and a probability for each of the 24 keys. Each database key then counts as a witness that is right about half the time (GetSongBPM 0.5, AcousticBrainz 0.35) and, when wrong, usually lands on a relative, parallel or fifth-neighbour key. A close audio call is easily tipped, a confident one needs two agreeing databases.

## Accuracy

Measured against human-labelled electronic music (Beatport previews; audio not included in this repo):

| | result |
|---|---|
| BPM, within ±4% of the Beatport BPM (GiantSteps-MTG, 885 clips) | 94.8% |
| Key, exact match, shipped committee detector (GiantSteps Key, 604 clips, cross-validated) | 63-64% exact; 43% of major keys found |
| Key, exact match, Essentia `edmm` profile alone (same clips) | 65% (weighted MIREX score 0.70); 0% of major keys found |
| Key, exact match, Essentia `bgate` profile (same clips) | 61% (0.68) |
| Key, exact match, Essentia `edma` profile (same clips) | 58% (0.65) |
| Key, exact match, classical Krumhansl profile (same clips) | 49% (0.59) |

Key detection is a small committee (`bpmkey/keydetect.py`): Essentia's `edmm` and `bgate` profiles plus the track's mean chroma vote on all 24 keys, with weights fitted on GiantSteps (`benchmark/keymodel_fit.py`). It replaced `edmm` alone because `edmm` can only answer minor: on GiantSteps it never produced a major key, so the 15% of clips that are major were always wrong, and a database saying "major" could never overrule it. The committee finds about 4 in 10 of the major keys at the same overall exact accuracy, and its probabilities are better calibrated (log-loss 1.59 to 1.31). Major vs minor stays the hardest call (mode AUC 0.78). `MODE_PRIOR_SHIFT` in `keydetect.py` sets how readily it says major: GiantSteps is 85% minor, so 0 keeps that prior (66% exact, 23% of majors found) and the shipped 1.0 assumes a mixed collection (63-64% exact, 43% of majors). The database reliabilities were estimated from a handful of tracks and the database-combination gains in `benchmark/db_sim.py` are simulated, so treat both as unverified until measured against labelled tracks from a real collection. The benchmark scripts and report are in `benchmark/` (`report_giantsteps.md`); its extra dependencies are in `benchmark/requirements.txt`.

Key detection by audio alone is the weak spot, so the database votes matter. A 90% exact-key target is not realistic for any current method.

## Known limitations

- Half/double tempo is ambiguous for some genres (e.g. footwork at 80 vs 160 BPM).
- Key detection is unreliable on atonal or heavily percussive music, and on tracks that change key.
- YouTube sometimes blocks downloads (403 or age-gating); the next source is tried automatically.
- Bandcamp is not used: its search is behind a bot challenge, and following artist and label pages found nothing on 7 tracks YouTube had missed, at about 20 s per track, before it was rate-limited.

## Data sources and credits

- BPM and key data provided by [GetSongBPM](https://getsongbpm.com).
- Release metadata from the [Discogs API](https://www.discogs.com/developers).
- Additional BPM data from [Deezer](https://developers.deezer.com) and [AcousticBrainz](https://acousticbrainz.org) via [MusicBrainz](https://musicbrainz.org).

This is a personal project and is not affiliated with any of the services above.

## Vinyl Second-Brain

A vinyl library app (Discogs intake, BPM/key analysis, notes, semantic search, generated Obsidian vault). Layout: `backend/` (FastAPI), `frontend/` (React, later), `vault/` (generated), `audio/` (your files, git-ignored), `docs/`, with the build plan in `building_plan/`. Use the single Python 3.11 env at `.venv`; `make dev`, `make test`, `make lint`.
