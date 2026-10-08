# bpm-key-tool

A personal tool that takes a [Discogs](https://www.discogs.com) release link and returns the **BPM** and **musical key (Camelot notation)** for every track.

It looks values up online first, compares the sources, and only analyses the audio when the online results are missing or disagree.

## Status

Work in progress.

- [x] Step 1: Discogs release URL → tracklist
- [ ] Step 2: find audio sources (YouTube, Bandcamp, iTunes preview)
- [ ] Step 3: online BPM/key lookup and comparison
- [ ] Step 4: audio analysis fallback (Essentia)
- [ ] Step 5: Camelot conversion, merging, caching

## Usage

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your Discogs token
python -m bpmkey.cli https://www.discogs.com/release/249504
```

## Data sources and credits

- BPM and key data provided by [GetSongBPM](https://getsongbpm.com).
- Release metadata from the [Discogs API](https://www.discogs.com/developers).
- Additional BPM data from [Deezer](https://developers.deezer.com) and [AcousticBrainz](https://acousticbrainz.org) via [MusicBrainz](https://musicbrainz.org).

This is a personal project and is not affiliated with any of the services above.
