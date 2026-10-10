# Progress

## Step 1: Project scaffold (done)
- Monorepo folders added next to `bpmkey/`; single Python 3.11 env at `.venv` (old 3.10 `.venv` and `.venv311` removed, `requirements.lock.txt` pins it).
- `backend/` FastAPI app with `GET /health`, pytest, ruff; root `Makefile` with `dev`, `test`, `lint`.

## Step 2: Database schema and migrations (done)
- `backend/app/db/`: plain sqlite3, `connect()` loads sqlite-vec and enables foreign keys; `migrate()` applies numbered `migrations/*.sql` tracked in `schema_version`.
- `0001_init.sql`: records, tracks, notes (CHECK exactly one parent), `note_embeddings` (vec0, 1536 dims, prose only, enforced in `notes.py`), tags + join tables, FTS5 over record artist/title/label and note bodies (trigger-synced).
- Data-access modules: records, tracks, notes, tags. Tests in `backend/tests/test_db.py`.
- Default DB path `backend/data/vinyl.db` (override with `DB_PATH`).

## Step 3: Discogs client and record intake (done)
- `backend/app/discogs.py`: httpx client with 429 backoff (honours `Retry-After`); URL and tracklist parsing are imported from `bpmkey.discogs`. Master URLs resolve to the main release.
- `POST /api/records/intake` `{discogs_url, status?}`: 201 created, 200 for an existing release (no refetch). Response includes `tracks` and `resolved_from_master`.
- Real fixtures (2 releases + 1 master, plus a double LP with C/D sides) in `backend/tests/fixtures/`. Verified once against the live API.
- `tracks.artist` added (migration 0002) because compilations differ from the record artist.

## Step 4: Audio analysis (done)
- `analysis/engine.py`: `analyze(path)` wraps bpmkey's committee key model and Essentia BPM; `bpm_alt` (half/double) and key scores go in `analysis_raw`.
- `analysis/matching.py`: files in `audio/<discogs_release_id>/` match by filename position, then fuzzy title; ambiguous or duplicate claims are reported, never guessed. `GET /api/records/{id}/audio-match` previews it.
- `jobs` table + `JobRunner` (worker thread, restart recovery). `POST /api/records/{id}/analyze` (202) and `GET /api/jobs/{id}`. One failing file does not block the rest.
- Run with `make dev` / `make test` (both put the repo root on the path so `bpmkey` imports).
