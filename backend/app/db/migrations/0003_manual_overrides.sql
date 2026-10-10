-- A hand-entered BPM or key is locked against re-analysis until the user unlocks it.
ALTER TABLE tracks ADD COLUMN bpm_manual INTEGER NOT NULL DEFAULT 0 CHECK (bpm_manual IN (0, 1));
ALTER TABLE tracks ADD COLUMN key_manual INTEGER NOT NULL DEFAULT 0 CHECK (key_manual IN (0, 1));
