# Spin Count

A personal vinyl library. Paste a Discogs link and the record, its tracklist, and every track's BPM and key
(Camelot or musical) land in your library; add notes and tags, find records by tempo, key or tag, and read the
whole collection in Obsidian. The BPM and key come from [bpmkey](#bpmkey-the-bpm-and-key-lookup-engine), below.

```
Discogs link ──> intake ──> SQLite (the only place anything is written)
                   │            ├── analysis job: BPM + key via bpmkey      (no audio files needed)
                   │            ├── Discogs job:  add to your collection    (owned records only)
                   │            └── vault sync:   generated Obsidian files  (overwritten each sync)
                   └──> web app (React) on the same port as the API (FastAPI)
```

## Run it

You need Python 3.11 (Anaconda is fine) and, once, a [Discogs personal token](https://www.discogs.com/settings/developers)
("Generate new token"). Then, in this folder:

```bash
make run          # first time: creates .env, the Python env (.venv), a Node env (.nodeenv), builds, serves
```

Put your token in `.env` (`DISCOGS_TOKEN=...`, and `CONTACT_EMAIL=...` for polite API headers), run `make run` again,
and open <http://127.0.0.1:8000>. Press `n` to add a record, `/` to search. The server listens on localhost only and
has no login, so do not expose the port.

| Command | What it does |
| --- | --- |
| `make run` | build the app and serve it on port 8000 (`PORT=8100 make run` to change) |
| `make dev` + `make frontend-dev` | API with auto-reload, and the Vite dev server on :5173 with live reload |
| `make test-all` | backend tests, frontend component tests, browser tests (`make test`, `make test-frontend`, `make e2e`) |
| `make lint`, `make coverage` | ruff, and a coverage report |
| `make backup` | copy the database to `backend/backups/` now |
| `make sync-vault` | rebuild the Obsidian files now (the app also does this a couple of seconds after any change) |
| `make backfill-styles` | fetch Discogs styles (and catalogue number, year if missing) for records added before styles existed; calls Discogs once per record |
| `make openapi`, `make types` | re-export `docs/openapi.json`, and regenerate the frontend's API types from it |

Data lives in `backend/data/vinyl.db`, your audio in `audio/`, the Obsidian files in `vault/`. Paths and other settings
are in `.env` (see `.env.example`).

## Obsidian

Open the `vault/` folder as a vault (Obsidian: *Open folder as vault*) and enable the **Dataview** community plugin.
`Records/` holds one note per record with its BPM range, keys, tags, tracklist and notes in the frontmatter and body;
`Dataview Examples.md` has ready-made queries by BPM, key and tag.

The vault is **generated output**. Edits made in Obsidian are overwritten on the next sync, because the database is the
only place anything is written. Your own notes in `Records/` are never deleted (only files the app generated are).
To keep your own Obsidian notes, put them outside `Records/`, or point `VAULT_DIR` at a folder inside a bigger vault.

## Labels

On a record page, **Make label** opens a preview and editor for two 62 × 40 mm labels (696 × 472 px, 1-bit PNG, ready
for a Brother QL with 62 mm tape): the **main label** (artist, label and cat#, title, a QR code to the Discogs page, year,
country, styles and a one-sentence note) and the **tracks label** (per side a black block, then position, BPM, Camelot
key, tags and the track note; a long tracklist continues on a second label). Every field can be edited or hidden with
its tick, tracks can be skipped, and the preview warns when text had to be cut. Edits are for that print only: the
record is not changed. Country is not stored anywhere, so type it in if you want it. **Download** saves the PNGs;
printing straight to the Brother (`brother_ql`) is not wired in yet.

## Audio files (optional)

BPM and key do not need audio: bpmkey looks them up online and, when the databases disagree, finds and analyses the
audio itself. If you have your own rips, drop them in `audio/<discogs release id>/` (the number in the Discogs URL),
named like `A1 - Title.wav`. They are matched to tracks by position, then by title, and **override** the lookup for
the tracks they match. Anything that does not match is listed on the record page, where you can assign it by hand.
A BPM or key you enter by hand is marked *manual* and is never overwritten by re-analysis (the x unlocks it).

## Backups

`make backup` writes a consistent, timestamped copy of the database to `backend/backups/` (safe while the app runs).
For a nightly backup at 03:00 on macOS (runs at wake-up if the Mac was asleep; keeps the newest 14):

```bash
deploy/install-nightly-backup.sh            # install
deploy/install-nightly-backup.sh --remove   # uninstall
```

## Docker (untested)

`Dockerfile` and `docker-compose.yml` are provided for running on a server or NAS. **They have never been built or run**:
Docker was not available where this was developed. `make run` is the supported way.

## Not built yet

- Search **by meaning** (finding "banging track" from "huge energy"): the plumbing is in place, but no embedding model
  is configured, so the Search page offers exact word search until one is plugged in (`backend/app/deps.py`).
- Printing labels straight to the Brother QL (labels can be downloaded as PNG today).
- Two-way Obsidian sync, playlist and set building by Camelot compatibility.

## Layout

`backend/` FastAPI app, SQLite schema and tests · `frontend/` React app, component and browser tests · `bpmkey/` the
lookup engine · `benchmark/` how its accuracy was measured · `vault/` generated Obsidian files · `audio/` your files ·
`docs/` progress notes and the exported OpenAPI schema · `building_plan/` the original plan.

---

# bpmkey (the BPM and key lookup engine)

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
