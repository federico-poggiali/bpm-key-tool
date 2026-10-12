-- Tags are designed in the Tag Manager and live in a group. Energy, atmosphere and set role are fixed
-- groups; any other group is the user's own. The old free-text tags are dropped (notes carry prose now).
CREATE TABLE tag_groups (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    fixed INTEGER NOT NULL DEFAULT 0 CHECK (fixed IN (0, 1)),
    position INTEGER NOT NULL DEFAULT 0
);
INSERT INTO tag_groups(name, fixed, position) VALUES ('Energy', 1, 0), ('Atmosphere', 1, 1), ('Set role', 1, 2);

DELETE FROM tags;  -- links go with them (ON DELETE CASCADE)
ALTER TABLE tags ADD COLUMN group_id INTEGER REFERENCES tag_groups(id) ON DELETE CASCADE;
