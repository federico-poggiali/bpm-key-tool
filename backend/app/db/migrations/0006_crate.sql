-- Crate: the owner's physical shelving. A unit (e.g. a 4x4 Kallax) sits on a wall grid at x/y,
-- measured in cubes; each cube can be split by dividers into sections, and a record lives in one
-- section. section_id NULL = unsorted (not yet placed).
CREATE TABLE shelf_units (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    rows INTEGER NOT NULL CHECK (rows BETWEEN 1 AND 8),
    cols INTEGER NOT NULL CHECK (cols BETWEEN 1 AND 8),
    x INTEGER NOT NULL DEFAULT 0 CHECK (x >= 0),
    y INTEGER NOT NULL DEFAULT 0 CHECK (y >= 0)
);
CREATE TABLE cubes (
    id INTEGER PRIMARY KEY,
    unit_id INTEGER NOT NULL REFERENCES shelf_units(id) ON DELETE CASCADE,
    row INTEGER NOT NULL,
    col INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    UNIQUE (unit_id, row, col)
);
-- Sections run left to right inside a cube; every cube keeps at least one.
CREATE TABLE cube_sections (
    id INTEGER PRIMARY KEY,
    cube_id INTEGER NOT NULL REFERENCES cubes(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_cube_sections_cube ON cube_sections(cube_id);
ALTER TABLE records ADD COLUMN section_id INTEGER REFERENCES cube_sections(id) ON DELETE SET NULL;
CREATE INDEX idx_records_section ON records(section_id);
