-- Discogs styles (e.g. 'Deep House') live on the record; tracks inherit them.
-- styles: NULL = never fetched (existing records), '[]' = Discogs has none.
-- styles_manual: a hand-edited list is locked against re-fetching until the user resets it.
ALTER TABLE records ADD COLUMN styles TEXT CHECK (styles IS NULL OR json_valid(styles));
ALTER TABLE records ADD COLUMN styles_manual INTEGER NOT NULL DEFAULT 0 CHECK (styles_manual IN (0, 1));
ALTER TABLE records ADD COLUMN catno TEXT;
