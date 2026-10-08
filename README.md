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
python -m bpmkey https://www.discogs.com/release/10296528
```

Options: `--no-analyze` (online lookups only), `--refresh` (ignore the cache), `--csv out.csv`, `--tracks-only`, `-v`.

Tracks are marked `agreed` when sources agree, `analyzed` when the audio analysis overruled or replaced the online values, `single` when only one source answered, and `conflict`/`none` otherwise.

## How it works

1. Look the track up in GetSongBPM, Deezer and AcousticBrainz.
2. If BPM and key are confirmed by at least two sources, stop.
3. Otherwise download the audio (matched by title and duration, ±6 s), analyze the whole track with Essentia, and let the result break the tie.

## Known limitations

- Half/double tempo is ambiguous for some genres (e.g. footwork at 80 vs 160 BPM).
- Key detection is unreliable on atonal or heavily percussive music.
- YouTube sometimes blocks downloads (403 or age-gating); the next source is tried automatically.

## Data sources and credits

- BPM and key data provided by [GetSongBPM](https://getsongbpm.com).
- Release metadata from the [Discogs API](https://www.discogs.com/developers).
- Additional BPM data from [Deezer](https://developers.deezer.com) and [AcousticBrainz](https://acousticbrainz.org) via [MusicBrainz](https://musicbrainz.org).

This is a personal project and is not affiliated with any of the services above.
