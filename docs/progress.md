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

## Step 6: Notes and tags API (done)
- Records: `GET /api/records` (filters `bpm_min`, `bpm_max`, `key` musical or Camelot, repeatable `tag`, `status`, `q`, `limit`/`offset`), `GET/PATCH/DELETE /api/records/{id}`. The detail response nests tags, record notes and per-track notes.
- BPM and key filters must match on the same track; the response lists `matched_track_ids`. A tag matches the record or any of its tracks (all given tags required). `q` searches artist/title/label and note bodies (record and track notes).
- Tracks: `GET /api/tracks` with the same filters (a tag also matches via the parent record; `q` also matches track title/artist), `GET /api/tracks/{id}`, `PATCH` for manual BPM/key.
- **Manual input is always possible and wins:** setting `bpm` or `key` locks that field (`bpm_manual`/`key_manual`); re-analysis then only records its own result in `analysis_raw`. `unlock: ["bpm"|"key"]` hands a field back to analysis. Keys accept musical or Camelot input (migration 0003).
- Notes: `POST/PATCH/DELETE /api/notes` (exactly one of `record_id`/`track_id`). Tags: `GET /api/tags` (counts), add/remove on records and tracks.
- Moving a record to `owned` queues the Discogs sync (never removes anything from Discogs); deleting a record leaves Discogs untouched.
- One error format `{"error": {"code", "message", "details"?}}` and one list envelope `{items, total, limit, offset}`; pydantic response models for the new endpoints (`app/schemas.py`).

## Step 7: Semantic search (plumbing done; no real provider yet)
- `embeddings/`: provider interface (1536 dims) and a deterministic fake for tests. **The OpenAI provider and its config were removed on request; to be revisited later** (a local or hosted model plugs in at `deps.get_embedder`). Vectors are normalised; the score is cosine similarity.
- Only `prose` notes are embedded: on create, re-embedded on edit, removed on delete, on a type change away from prose, and when a record or track is deleted (cascades do not reach the vec table). A provider failure or a missing key never loses a note.
- `GET /api/search/semantic?q=&limit=` returns notes with their record/track and score; `POST /api/admin/reembed` rebuilds everything. Both return 503 until a provider is configured.
- Not done yet: any real model, so no synonym search ('banging' finds 'huge energy') until one is chosen.

## Step 8: Obsidian vault generator (done)
- `app/vault.py` (CLI: `make sync-vault`, API: `POST /api/admin/sync-vault`, status: `GET /api/admin/vault-status`): one file per record in `vault/Records/<Artist> - <Title> (<release_id>).md`, fully regenerated from the DB. Frontmatter: discogs_id, artist, title, label, year, format, status, tags, bpm_min/max, keys, camelot_keys; a do-not-edit banner; tracklist table (manual values marked); record notes; track notes under their track. Wantlist/considering get their own files with `status` in the frontmatter.
- Writes are atomic and skipped when unchanged. Stale files are deleted, but only ones carrying the `generated_by: vinyl-second-brain` marker, so your own notes in `Records/` are safe.
- `vault/Dataview Examples.md` has four queries (BPM range, key, tag, wantlist).
- Sync is debounced (2 s) after any successful write request and after every background job, and runs once at startup. Snapshot test: `tests/fixtures/vault_expected.md`.
- Not verified by me: opening `vault/` in Obsidian with the Dataview plugin and checking that the queries render.

## Step 9: Backend hardening (done)
- JSON request/app logs (`LOG_LEVEL`), a global handler for unexpected errors in the standard error format, CORS for `http://localhost:5173` and `http://127.0.0.1:5173` (`CORS_ORIGINS`), SQLite in WAL mode with a 10 s busy timeout (the job worker and the API write concurrently).
- OpenAPI: every endpoint has a documented success schema and a readable `operationId` (tests enforce it); `docs/openapi.json` is exported with `make openapi` and a test fails if it goes stale.
- `make backup` writes a timestamped consistent copy to `backend/backups/` (git-ignored).
- 95 tests, stable over 4 consecutive runs; coverage 94% (`make coverage`).

## Batches E-H: frontend and shipping (Steps 10-17, done)
Style: the bpmkey UI's design system ("Spin Count": Booth/Strobe/Concrete/Signal, system fonts, mono micro-labels, dark and light by system setting) ported to `frontend/src/styles/tokens.css`. One deviation: `--ink-3` (small grey text) was lifted from `#7b7b75`/`#6d6d67` to `#898983`/`#5c5c56` because the original misses WCAG AA contrast (4.16:1 light, 3.99:1 dark on raised surfaces). CSS Modules per component; no Tailwind.

- **Step 10 shell:** Vite + React 19 + TypeScript, React Router, TanStack Query; left nav (Library, Wantlist, Search, Add record, Settings) that becomes a top bar under 760 px; API health LED; dev proxy (`BACKEND_URL`). Types are generated from `docs/openapi.json` (`make types`). TypeScript is pinned to 5.x because `openapi-typescript` does not work with TypeScript 7.
- **Step 11 Add record:** URL + status, job chips for Analysis and Discogs sync (polling, retry), duplicate message with link, master-link note, and an audio panel to assign unmatched files by hand (new `POST/DELETE /api/tracks/{id}/audio`; assigned files are matched first).
- **Step 12 Library:** grid, table and track views; BPM two-handle slider, key picker (Camelot or musical, remembered), tag picker with counts, status, debounced text search; all filters in the URL (back button restores them); pagination, skeletons, empty states. List items now carry `bpm_min`, `bpm_max`, `camelot_keys`.
- **Step 13 Record page:** tracklist with low-confidence flag (a word, not a colour) and one-click half/double BPM; click-to-edit BPM and key (marked manual, unlock with the x); notes grouped by type with autosave and a Saving/Saved indicator; tag editors with autocomplete for record and tracks; optimistic updates with rollback.
- **Step 14 Search:** By meaning (default) and Exact (`GET /api/search/exact`, highlighted snippets); results open the record scrolled to the note. By meaning shows a clear "not set up yet" notice until an embedding provider exists.
- **Step 15 Settings:** vault folder, last sync time and counts, Sync now, warning that Obsidian edits are overwritten, reveal the Dataview examples in Finder (`POST /api/admin/open-vault`).
- **Step 16 polish:** error boundary, toasts for failed requests, skeletons, shortcuts (`/` search, `n` add; ignored while typing), automated axe accessibility checks on every page in both themes (zero serious violations). 19 Vitest tests (filter bar, note editor, URL state) and 19 Playwright tests (3 flows: add record to note to search to vault, filters with the back button, settings; plus 16 axe page checks). The browser tests run the real app on a throwaway DB/vault with Discogs and the BPM lookup faked (`backend/tests/e2e_server.py`).
- **Step 17:** `make run` builds and serves everything on one port (sets up `.venv` and `.nodeenv` on first use); `make backup` keeps the newest 14; `deploy/install-nightly-backup.sh` installs a 03:00 launchd job (not installed by me); README rewritten; `Dockerfile` and `docker-compose.yml` written but **untested** (no Docker here).
- **Bugs found by running it for real:** FastAPI opens and closes the DB dependency on different threads, which SQLite rejected (500s under the browser, invisible to the unit tests; fixed with `check_same_thread=False` and a regression test); the Add page requested record 0 before anything was added.

## Discogs styles, catalogue number and year (done)
Plan: `genre-plan.md`. Decisions: styles only (broad genres are never stored, except as a stand-in when a release has no styles); tags stay separate and user-only; tracks inherit from their record.
- Migration `0004_styles.sql`: `records.styles` (JSON array; NULL = never fetched, `[]` = none), `records.styles_manual`, `records.catno`. Styles come from the same `/releases/{id}` response used at intake, so no extra API call.
- Styles are editable (`PATCH /api/records/{id}` with `styles`): names are trimmed and de-duplicated case-insensitively, and the edit sets `styles_manual`, so the backfill and re-fetches never overwrite it. `{"reset_styles": true}` releases the lock and re-fetches from Discogs.
- Filters: repeatable `style` parameter on `GET /api/records` and `GET /api/tracks` (case-insensitive, all must match, combines with BPM/key/tag). `GET /api/styles` lists every style with its record count.
- Year: already stored per record; the importer now also falls back to Discogs' `released` date when `year` is missing. Tracks expose `year` and `styles`, inherited from their record at query time (one source of truth, so editing the record updates every track).
- Backfill for existing records: `make backfill-styles`, or Settings > "Fetch styles for existing records" (job `backfill_styles`, `POST /api/admin/backfill-styles`). Fills only NULL, unedited records (plus a missing catno/year); a second run only retries failures. **Not run against the real library yet**: it calls Discogs once per record.
- Vault: `styles` and `catno` in the frontmatter, a "Records by style" Dataview example.
- Frontend: style filter (URL `style=`), chips on grid cards, a Styles column in the table and tracks views, a style editor on the record page with an "edited" mark and "Reset to Discogs", catno next to the label, Year column in the tracks view.
- Not done: styles are not in the exact-search index, so typing "dub techno" in search does not find records by style (use the style filter).
- Tests: 116 backend, 26 frontend, 20 browser (new: style filter with the back button, edit/reload/reset flow).

## Record labels (done)
Plan: `LABEL_PLAN.md`. Decisions: Pillow drawing (not HTML + Chromium) so the preview is exactly what prints; the feature lives in the app; **download only** for now (no `brother_ql` yet); no new database columns, so country and category are not stored (country is an optional typed-in field, category is dropped; tags are shown instead).
- `backend/app/labels/`: `data.py` (`LabelData`, the builder from `record_detail`: strips Discogs "(2)", first sentence of the prose note, Camelot key, QR to the Discogs release) and `render.py` (696 x 472 px, text drawn without anti-aliasing, DejaVu Sans/Mono Bold bundled in `labels/fonts/`, text fitting that shrinks, wraps and finally cuts with a warning, tracklist pagination across labels).
- API: `GET /api/records/{id}/label` (defaults from the database; 404 for a record not in the library) and `POST /api/records/{id}/label/render` (edited `LabelData` in, base64 PNGs plus warnings out; stores nothing and does not trigger a vault sync).
- Frontend: `/records/:id/label` (editor with print ticks per field and per track, skip-track, live debounced preview, Reset edits, Download per label or all) and a "Make label" button on the record page.
- New dependencies: Pillow, qrcode (in `requirements.lock.txt` and `pyproject.toml`).
- Not done from the plan: "Save to database" write-back, the AI "rewrite note" helper (no LLM provider), the `make-label` CLI and batch printing, `brother_ql` printing.
- Tests: 133 backend (17 new), 34 frontend (8 new), 23 browser (1 new flow, 2 new axe checks).

## Crate: the physical shelf (done)
Decisions: shelving is drawn as units of cubes (IKEA Kallax/Eket style); a cube can be split by dividers into sections, and a record lives in one section; records are placed on the Crate page only; **no backfill** (location is physical data nobody can fetch): every owned record starts in Unsorted, and each gets a suggested section instead.
- Migration `0006_crate.sql`: `shelf_units` (name, rows/cols up to 8, wall position x/y in cubes), `cubes` (name/tag, description), `cube_sections` (dividers, left to right), `records.section_id` (NULL = unsorted; deleting a unit or shrinking it sends its records back to unsorted).
- API (`routes/crate.py`, every write returns the whole shelf): `GET /api/crate`, `POST/PATCH/DELETE /api/crate/units[/{id}]` (409 when units would overlap), `PATCH /api/crate/cubes/{id}`, `POST /api/crate/cubes/{id}/sections` (add a divider), `PATCH/DELETE /api/crate/sections/{id}` (removing a divider merges its records into the neighbour; a cube keeps one), `PUT /api/crate/place` (many records into a section, or `null` for unsorted).
- Suggestions (`db/crate.py`): a record's tags and styles against the unit, cube and section names and the cube description (a tag/style named in full scores 2, a shared word 1), plus the artist's initial inside a letter range like "A–M" (leading "The" ignored). Wantlist records are never on the shelf.
- Frontend: `/crate`, listed under the top-right Library menu. **Dig** mode: the wall with record spines per section, drag records from the right-hand panel onto a section (or use the "Move to" select), one-click suggestions, "Where is…" search that lights up the cube. **Build** mode: add units (presets 1×1 to 5×5 or custom), drag a unit by its name tag (or arrow keys) to move it, resize/rename/delete; click a cube to name it, describe it and add dividers.
- Ask on arrival: adding a record as owned (Add page) or pressing "Add to library" opens the record with a "Where does it go?" card (suggested spot, any cube/section, or Later). It shows only when a shelf exists and the record is unsorted (`components/ShelfPrompt.tsx`).
- Tests: 144 backend (7 new), 2 new browser flows, 2 new axe checks; the full browser suite passes (30).
- A running `make run` server must be restarted to pick up the crate API and migration 0006.
