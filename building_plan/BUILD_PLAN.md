# Vinyl Second-Brain: Build Plan for Claude Code

How to use this file: put it in the repo root. Give Claude Code one step at a time ("Do Step 3 from BUILD_PLAN.md"). Don't move on until the step's **Done when** checks pass. Commit after every step.

## Ground rules (paste once at the start of the session, or put in CLAUDE.md)

- The database is the ONLY place anything is written. Obsidian markdown is generated output and is overwritten on every sync. Never build two-way sync.
- Backend: Python 3.12, FastAPI, SQLite, `sqlite-vec`, SQLAlchemy or plain `sqlite3` (keep it simple), pytest.
- Frontend: React + Vite + TypeScript, talking to the backend over a JSON REST API.
- Monorepo layout: `backend/`, `frontend/`, `vault/` (generated Obsidian files), `audio/` (user audio files, git-ignored), `docs/`.
- Every step ends with tests or a manual check, and a short note in `docs/progress.md`.
- Secrets (Discogs token, OpenAI key) live in `.env`, never committed. Provide `.env.example`.

## Defaults chosen for the six open decisions

These can be changed later; they are chosen so you can start now.

| Decision | Default |
| --- | --- |
| Note types | Open string field, UI suggests `prose`, `cue-points`, `location`, `purchase`, `condition` |
| Obsidian body | Fully auto-rendered from the DB on every sync; edits in Obsidian are discarded |
| Embeddings | OpenAI `text-embedding-3-small`, behind a provider interface so a local model can replace it |
| Tags | Freeform, with autocomplete from existing tags and Discogs genres/styles |
| Obsidian plugins | Dataview only for v1 |
| Wantlist / non-owned records | A `status` column on records (`owned`, `wantlist`, `considering`); default `owned` |

---

# PART 1: BACKEND

## Step 1: Project scaffold

**Goal:** Empty but runnable monorepo.

**Instructions for Claude Code:**
1. Create the folder layout above, a root `README.md`, `.gitignore` (include `.env`, `audio/`, `*.db`, `node_modules`, `vault/`), and `.env.example` with `DISCOGS_TOKEN`, `OPENAI_API_KEY`, `DB_PATH`, `AUDIO_DIR`, `VAULT_DIR`.
2. In `backend/`, set up a Python project (`pyproject.toml`), a FastAPI app with a `GET /health` endpoint, and pytest with one passing test.
3. Add a `Makefile` (or `justfile`) with `dev`, `test`, `lint` targets.

**Done when:** `make test` passes and `GET /health` returns `{"status":"ok"}`.

## Step 2: Database schema and migrations

**Goal:** The four entities from the architecture, with vector support.

**Instructions for Claude Code:**
1. Use SQLite with the `sqlite-vec` extension loaded on connect. Add a simple migration system (numbered `.sql` files plus a `schema_version` table).
2. Tables:
   - `records`: id, discogs_release_id (unique, nullable), artist, title, label, year, format, cover_url, status (`owned|wantlist|considering`), added_at, discogs_collection_synced (bool)
   - `tracks`: id, record_id (FK, cascade), position (e.g. `A1`), title, duration_sec, bpm, key, camelot_key, confidence, analysis_raw (JSON), audio_path (nullable), analyzed_at
   - `notes`: id, type (free text), body, record_id (nullable FK), track_id (nullable FK), created_at, updated_at. Add a CHECK that exactly one of record_id / track_id is set.
   - `note_embeddings`: a `sqlite-vec` virtual table keyed by note id. Only notes with `type='prose'` get a row.
   - `tags`: id, name (unique, lowercase). `record_tags` and `track_tags` join tables.
3. Add a full-text search virtual table (FTS5) over note bodies, record artist/title/label.
4. Write a small data-access layer (`backend/app/db/`) with functions for CRUD on each entity. No business logic in route handlers.

**Done when:** tests create a record, tracks, notes (record-level and track-level), and tags, and the exactly-one-parent constraint rejects bad notes.

## Step 3: Discogs client and record intake (metadata only)

**Goal:** Paste a Discogs link, get a record plus its tracklist in the DB.

**Instructions for Claude Code:**
1. Write `discogs.py`: parse a Discogs URL (release or master URL) into a release ID; fetch the release from the Discogs API using the personal token; respect rate limits (retry with backoff on 429).
2. Map the response to a Record and its Track rows (position, title, duration). Handle multi-disc/side positions like `A1`, `B2`, `C1`, and skip heading rows.
3. `POST /api/records/intake` with body `{ "discogs_url": "..." }`: creates the record and tracks, returns the full record. If the release ID already exists, return the existing record with HTTP 200 instead of duplicating.
4. Mock the Discogs API in tests with saved JSON fixtures (store 2-3 real responses in `backend/tests/fixtures/`).

**Done when:** posting a real Discogs link creates one record and the correct number of tracks; posting it twice does not duplicate.

## Step 4: Audio analysis (BPM and key)

**Goal:** Analyze audio files and fill BPM, key, confidence for each track.

**Important gap to resolve first:** Discogs provides no audio. Analysis needs audio files. Default design: you put files (ripped vinyl or digital copies) in `audio/<release_id>/`, and the app matches them to tracks. Ask me if this should be different.

**Instructions for Claude Code:**
1. Create an `analysis/` module with a single interface: `analyze(path) -> {bpm, key, camelot_key, confidence, raw}`. Implement it with Essentia if it installs cleanly; otherwise `librosa` for BPM and a key-estimation approach (Krumhansl profiles). Keep the engine swappable behind the interface.
2. Convert musical keys to Camelot notation in a helper, with unit tests.
3. Matching: given the files in `audio/<release_id>/`, match them to tracks by position in the filename (`A1`, `B2`) first, then by fuzzy title match. Return a match report listing unmatched files and unmatched tracks. Never guess silently.
4. Analysis runs as a background job (FastAPI background task or a small queue table `jobs`: id, type, status, error, created_at). Endpoints:
   - `POST /api/records/{id}/analyze` starts the job
   - `GET /api/jobs/{id}` returns status
5. Store the tool's raw output in `tracks.analysis_raw` and the confidence score. Half/double-tempo errors are common: store the primary BPM and also a `bpm_alt` value (half or double) in the raw JSON.

**Done when:** analyzing a folder with 2-3 short test audio files fills BPM/key/confidence on the right tracks, and a mismatched filename shows up in the match report.

## Step 5: Discogs collection write-back

**Goal:** After intake, the record is also added to your Discogs collection, independently of analysis.

**Instructions for Claude Code:**
1. Add `add_to_collection(release_id)` to the Discogs client (default folder).
2. Make this a separate job from analysis, so one failing never blocks the other. Set `discogs_collection_synced` on success; store the error on failure.
3. Intake now creates the record, then enqueues two independent jobs: analysis (if audio exists) and collection sync. Add `POST /api/records/{id}/sync-discogs` to retry manually.
4. Respect `status`: only `owned` records are added to the collection. Wantlist records are not.

**Done when:** a successful intake marks the record synced; a simulated Discogs failure leaves analysis unaffected and is retryable.

## Step 6: Notes and tags API

**Goal:** Full CRUD for everything the frontend will edit.

**Instructions for Claude Code:**
1. Endpoints:
   - Records: `GET /api/records` (filters below), `GET /api/records/{id}`, `PATCH /api/records/{id}`, `DELETE /api/records/{id}`
   - Tracks: `PATCH /api/tracks/{id}` (manual BPM/key override, flagged so re-analysis does not clobber it)
   - Notes: `POST /api/notes`, `PATCH /api/notes/{id}`, `DELETE /api/notes/{id}`; a note takes either `record_id` or `track_id`
   - Tags: `GET /api/tags` (with counts), `POST /api/records/{id}/tags`, `DELETE /api/records/{id}/tags/{name}`, same for tracks
2. `GET /api/records` filters: `bpm_min`, `bpm_max`, `key` (accepts musical or Camelot), `tag` (repeatable), `status`, `q` (full-text), plus pagination. BPM/key filters match if ANY track on the record matches, and the response says which tracks matched.
3. Add a track-level search endpoint `GET /api/tracks` with the same filters, since DJ use is track-centric.
4. Input validation with Pydantic; consistent error format.

**Done when:** tests cover every endpoint and each filter combination, including a track-level note and a record-level note.

## Step 7: Semantic search

**Goal:** "Huge energy, crowd goes off" finds "banging track."

**Instructions for Claude Code:**
1. Create an `embeddings/` module with a provider interface (`embed(texts) -> vectors`) and an OpenAI implementation. Add a fake deterministic provider for tests.
2. Embed only `type='prose'` notes. Re-embed when a prose note's body changes; delete the embedding when the note is deleted or its type changes away from prose. Do this synchronously on save for v1, but isolate it in one function so it can move to a queue later.
3. `GET /api/search/semantic?q=...&limit=20`: embed the query, run the nearest-neighbour query via `sqlite-vec`, and return matching notes with their parent record/track and a similarity score.
4. `POST /api/admin/reembed` to rebuild all embeddings (needed when changing the model).

**Done when:** with the fake provider, tests prove embed-on-save, re-embed-on-edit, and cleanup-on-delete; with the real provider, a manual query for a synonym returns the right note.

## Step 8: Obsidian vault generator

**Goal:** One generated markdown file per record.

**Instructions for Claude Code:**
1. Write `sync_vault.py` (also exposed as `POST /api/admin/sync-vault` and a CLI command) that renders `vault/Records/<Artist> - <Title> (<release_id>).md` for every record.
2. Each file is **fully regenerated** from the DB, with this shape:
   - YAML frontmatter: `discogs_id`, `artist`, `title`, `label`, `year`, `format`, `status`, `tags`, `bpm_min`, `bpm_max`, `keys`, `camelot_keys`
   - A "do not edit, generated file" banner
   - Body: a tracklist table (position, title, BPM, key, confidence), then record-level notes, then track-level notes under their track
3. Delete files for records that no longer exist in the DB. Write atomically (temp file then rename) and skip writes when content is unchanged, so Obsidian doesn't churn.
4. Wantlist/considering records get their own file with `status` in frontmatter so Dataview can separate them.
5. Trigger a sync after any DB write (debounced), plus the manual endpoint.
6. Also generate `vault/Dataview Examples.md` with 3-4 ready-made Dataview queries (by BPM range, by key, by tag).

**Done when:** a snapshot test compares generated markdown for a fixture record, and opening the `vault/` folder in Obsidian shows the Dataview examples working.

## Step 9: Backend hardening

**Instructions for Claude Code:**
1. Add structured logging, a global exception handler, and CORS configured for the frontend dev origin.
2. Add an OpenAPI check: confirm `/docs` lists every endpoint with accurate schemas (the frontend will generate types from it).
3. Add a backup command that copies the SQLite file with a timestamp.
4. Run the full test suite, fix flakiness, and report coverage.

**Done when:** all tests pass and `openapi.json` is exported to `docs/openapi.json`.

---

# PART 2: FRONTEND

## Step 10: Frontend scaffold

**Instructions for Claude Code:**
1. Create the Vite + React + TypeScript app in `frontend/`. Add React Router, TanStack Query for data fetching, and a lightweight UI approach (Tailwind or CSS modules; pick one and stay consistent).
2. Generate typed API client code from `docs/openapi.json` (e.g. `openapi-typescript`), wrapped in a thin `api.ts`.
3. App shell: left nav (Library, Wantlist, Search, Add Record), dark theme by default, responsive down to tablet width.
4. Configure the dev proxy to the backend.

**Done when:** `npm run dev` shows the shell and a health indicator that reads `/health`.

## Step 11: Add Record flow

**Goal:** The intake experience.

**Instructions for Claude Code:**
1. "Add Record" page: one input for a Discogs URL, a status selector (owned / wantlist / considering), and a submit button.
2. After submit, show the created record and tracklist, with job status chips for **Analysis** and **Discogs sync** that poll `/api/jobs/{id}` until done or failed, each with a retry button.
3. If the audio folder match report has unmatched files or tracks, show them and let the user manually assign a file to a track.
4. Handle duplicates (existing record) with a clear "already in your library" message and a link.

**Done when:** pasting a Discogs link goes end to end in the UI, with failures shown clearly and retryable.

## Step 12: Library view with filters

**Instructions for Claude Code:**
1. Library page: a record grid (cover art) with a toggle to a dense table view.
2. Filter bar: BPM range slider (two handles), key picker (toggle between musical and Camelot display), tag multi-select with counts, status, and a text search box. Filters live in the URL query string so views are shareable and survive refresh.
3. A "Tracks" toggle that switches the list to track-level results (from `GET /api/tracks`), showing artist, title, BPM, key, and the parent record.
4. Pagination or infinite scroll, loading and empty states.

**Done when:** every filter works alone and combined, and the back button restores filter state.

## Step 13: Record detail and editing

**Instructions for Claude Code:**
1. Record page: header (cover, metadata, status, Discogs link), tracklist table with BPM, key, and confidence (visually flag low confidence and show the alt half/double BPM).
2. Inline manual override for a track's BPM/key, clearly marked as manual.
3. Notes panel: list of notes grouped by type, add/edit/delete, a type field with suggestions plus free typing, a markdown textarea for the body. Notes can attach to the record or to a specific track (pick from the tracklist).
4. Tag editor with autocomplete for both the record and individual tracks.
5. Autosave with a visible saved/saving indicator, and optimistic updates.

**Done when:** you can add a prose note on one track, a location note on the record, edit a BPM by hand, and everything persists after reload.

## Step 14: Semantic search UI

**Instructions for Claude Code:**
1. Search page with one box and two result modes: **By meaning** (calls the semantic endpoint) and **Exact** (full-text). Default to meaning.
2. Results show the matching note snippet, the parent record/track, and a similarity indicator. Clicking opens the record page scrolled to that note.
3. Debounce input and cancel stale requests.

**Done when:** searching "crowd goes crazy" surfaces a note that says "huge energy, floor erupted".

## Step 15: Obsidian sync controls

**Instructions for Claude Code:**
1. Settings page: vault path (read from backend config, display only), "Sync vault now" button, last sync time, and count of files written/skipped/deleted.
2. A plain-language warning that edits made inside Obsidian are overwritten.
3. A button to open the Dataview examples file location.

**Done when:** clicking Sync updates the vault and the UI reports the result.

## Step 16: Polish, errors, and tests

**Instructions for Claude Code:**
1. Global error boundary, toast notifications for failed requests, skeleton loaders.
2. Keyboard shortcuts: `/` focuses search, `n` opens Add Record.
3. Accessibility pass: labels, focus order, contrast.
4. Add Vitest component tests for the filter bar and note editor, and one Playwright end-to-end test: add a record (mocked Discogs) → add a note → search for it → confirm it appears in the vault file.

**Done when:** the Playwright test passes in CI mode.

---

# PART 3: SHIPPING

## Step 17: Run it for real

**Instructions for Claude Code:**
1. Write a `docker-compose.yml` (or a single `make run`) that starts backend and a built frontend, with volumes for the DB, `audio/`, and `vault/`.
2. Document in the README: setup, getting a Discogs token, where to drop audio, how to point Obsidian at `vault/`, and the backup command.
3. Add a nightly backup task.

**Done when:** a fresh clone plus `.env` gets you a working app with one command.

## Later (do not build now)

- True two-way Obsidian sync (separate decision, hard problem)
- Local embedding model option
- Smart Connections plugin comparison
- Playlist/set-building views built on BPM and Camelot compatibility
