-- Analysis results wait here until the owner validates them; only then are they copied to tracks.
CREATE TABLE track_proposals (
    track_id INTEGER PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
    bpm REAL,
    key TEXT,
    camelot_key TEXT,
    confidence REAL,
    analysis_raw TEXT CHECK (analysis_raw IS NULL OR json_valid(analysis_raw)),
    audio_path TEXT,
    proposed_at TEXT NOT NULL
);
