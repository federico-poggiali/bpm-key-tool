# Progress

## Step 1: Project scaffold (done)
- Monorepo folders added next to `bpmkey/`; single Python 3.11 env at `.venv` (old 3.10 `.venv` and `.venv311` removed, `requirements.lock.txt` pins it).
- `backend/` FastAPI app with `GET /health`, pytest, ruff; root `Makefile` with `dev`, `test`, `lint`.

## Step 2: Database schema and migrations (done)
- `backend/app/db/`: plain sqlite3, `connect()` loads sqlite-vec and enables foreign keys; `migrate()` applies numbered `migrations/*.sql` tracked in `schema_version`.
- `0001_init.sql`: records, tracks, notes (CHECK exactly one parent), `note_embeddings` (vec0, 1536 dims, prose only, enforced in `notes.py`), tags + join tables, FTS5 over record artist/title/label and note bodies (trigger-synced).
- Data-access modules: records, tracks, notes, tags. Tests in `backend/tests/test_db.py`.
- Default DB path `backend/data/vinyl.db` (override with `DB_PATH`).
