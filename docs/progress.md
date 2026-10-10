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

## Step 4: Analysis (done; reworked in Step 5 to need no audio)
- `analysis/engine.py`: `analyze(path)` wraps bpmkey's committee key model and Essentia BPM; `bpm_alt` (half/double) and key scores go in `analysis_raw`.
- `analysis/matching.py`: files in `audio/<discogs_release_id>/` match by filename position, then fuzzy title; ambiguous or duplicate claims are reported, never guessed. `GET /api/records/{id}/audio-match` previews it.
- `jobs` table + `JobRunner` (worker thread, restart recovery). `POST /api/records/{id}/analyze` (202) and `GET /api/jobs/{id}`. One failing file does not block the rest.
- Run with `make dev` / `make test` (both put the repo root on the path so `bpmkey` imports).

## Step 5: Discogs collection write-back (done) and analysis from the link
- `DiscogsClient.add_to_collection` asks Discogs first and never adds a second copy (folder 1, "Uncategorized"); `remove_from_collection` exists for cleanup. Verified live once (add, duplicate guard, remove) on a throwaway release; the collection was left unchanged.
- `discogs_sync` job (`app/sync.py`): owned records only; sets `discogs_collection_synced`; failures are stored on the job and retryable via `POST /api/records/{id}/sync-discogs`.
- Intake now enqueues two independent jobs and returns their ids in `jobs` (`discogs_sync` is null for wantlist/considering; nothing is queued for an already-existing record).
- **Analysis no longer needs audio.** The job fetches the release and runs the bpmkey pipeline (online databases, then audio bpmkey finds itself). Files in `audio/<release_id>/` are optional and override the lookup for the tracks they match. `confidence` is the audio key confidence when audio was analysed, else null; the reconciliation status (`agreed`/`analyzed`/`single`/`conflict`) is in `analysis_raw`.
- Live check: release 9261843 (3 tracks) got BPM and key for all tracks from the link alone in about 66 s. A very obscure release (46673) returns nothing, the same as the bpmkey CLI.
