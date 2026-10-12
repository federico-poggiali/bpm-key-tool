-- Optional job input, e.g. {"track_ids": [..]} to analyse only some tracks of a record.
ALTER TABLE jobs ADD COLUMN params TEXT CHECK (params IS NULL OR json_valid(params));
