CREATE TABLE records (
    id INTEGER PRIMARY KEY,
    discogs_release_id INTEGER UNIQUE,
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    label TEXT,
    year INTEGER,
    format TEXT,
    cover_url TEXT,
    status TEXT NOT NULL DEFAULT 'owned' CHECK (status IN ('owned', 'wantlist', 'considering')),
    added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    discogs_collection_synced INTEGER NOT NULL DEFAULT 0 CHECK (discogs_collection_synced IN (0, 1))
);

CREATE TABLE tracks (
    id INTEGER PRIMARY KEY,
    record_id INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    position TEXT NOT NULL,
    title TEXT NOT NULL,
    duration_sec INTEGER,
    bpm REAL,
    key TEXT,
    camelot_key TEXT,
    confidence REAL,
    analysis_raw TEXT CHECK (analysis_raw IS NULL OR json_valid(analysis_raw)),
    audio_path TEXT,
    analyzed_at TEXT
);
CREATE INDEX idx_tracks_record ON tracks(record_id);
CREATE INDEX idx_tracks_bpm ON tracks(bpm);
CREATE INDEX idx_tracks_camelot ON tracks(camelot_key);

CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    body TEXT NOT NULL,
    record_id INTEGER REFERENCES records(id) ON DELETE CASCADE,
    track_id INTEGER REFERENCES tracks(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK ((record_id IS NULL) <> (track_id IS NULL))
);
CREATE INDEX idx_notes_record ON notes(record_id);
CREATE INDEX idx_notes_track ON notes(track_id);

-- Only notes with type='prose' get a row (enforced in the data-access layer).
CREATE VIRTUAL TABLE note_embeddings USING vec0(
    note_id INTEGER PRIMARY KEY,
    embedding FLOAT[1536]
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (name = lower(name))
);
CREATE TABLE record_tags (
    record_id INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (record_id, tag_id)
);
CREATE TABLE track_tags (
    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (track_id, tag_id)
);

-- Full-text search, kept in sync by triggers (rowid = source id).
CREATE VIRTUAL TABLE records_fts USING fts5(artist, title, label);
CREATE TRIGGER records_fts_ai AFTER INSERT ON records BEGIN
    INSERT INTO records_fts(rowid, artist, title, label)
    VALUES (new.id, new.artist, new.title, coalesce(new.label, ''));
END;
CREATE TRIGGER records_fts_au AFTER UPDATE ON records BEGIN
    DELETE FROM records_fts WHERE rowid = old.id;
    INSERT INTO records_fts(rowid, artist, title, label)
    VALUES (new.id, new.artist, new.title, coalesce(new.label, ''));
END;
CREATE TRIGGER records_fts_ad AFTER DELETE ON records BEGIN
    DELETE FROM records_fts WHERE rowid = old.id;
END;

CREATE VIRTUAL TABLE notes_fts USING fts5(body);
CREATE TRIGGER notes_fts_ai AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(rowid, body) VALUES (new.id, new.body);
END;
CREATE TRIGGER notes_fts_au AFTER UPDATE ON notes BEGIN
    DELETE FROM notes_fts WHERE rowid = old.id;
    INSERT INTO notes_fts(rowid, body) VALUES (new.id, new.body);
END;
CREATE TRIGGER notes_fts_ad AFTER DELETE ON notes BEGIN
    DELETE FROM notes_fts WHERE rowid = old.id;
END;
