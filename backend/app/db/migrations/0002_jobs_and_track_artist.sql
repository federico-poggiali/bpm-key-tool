-- Background jobs (analysis now, Discogs sync later).
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'done', 'failed')),
    record_id INTEGER REFERENCES records(id) ON DELETE CASCADE,
    error TEXT,
    result TEXT CHECK (result IS NULL OR json_valid(result)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_jobs_record ON jobs(record_id);
CREATE INDEX idx_jobs_status ON jobs(status);

-- Per-track artist (compilations and splits differ from the record artist).
ALTER TABLE tracks ADD COLUMN artist TEXT;
