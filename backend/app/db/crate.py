"""Crate: shelf units made of cubes, cubes split into sections, records placed in sections."""
import json
import re
import sqlite3
import unicodedata

from app.db import _util

_UNIT_COLUMNS = {"name", "rows", "cols", "x", "y"}
_CUBE_COLUMNS = {"name", "description"}
_SECTION_COLUMNS = {"name"}


class Overlap(ValueError):
    """Two units would occupy the same cubes on the wall."""


# --- layout -----------------------------------------------------------------------------------

def _check_free(conn: sqlite3.Connection, rect: dict, skip_id: int | None = None) -> None:
    for other in conn.execute("SELECT * FROM shelf_units WHERE id IS NOT ?", (skip_id,)):
        if (rect["x"] < other["x"] + other["cols"] and other["x"] < rect["x"] + rect["cols"]
                and rect["y"] < other["y"] + other["rows"] and other["y"] < rect["y"] + rect["rows"]):
            raise Overlap(f"overlaps '{other['name']}'")


def _fill_cubes(conn: sqlite3.Connection, unit_id: int, rows: int, cols: int) -> None:
    """Create the cubes a unit is missing (each with one section); drop those outside rows x cols.
    Records in a dropped cube go back to unsorted (section_id is set to NULL)."""
    conn.execute("DELETE FROM cubes WHERE unit_id = ? AND (row >= ? OR col >= ?)", (unit_id, rows, cols))
    for r in range(rows):
        for c in range(cols):
            cur = conn.execute("INSERT OR IGNORE INTO cubes(unit_id, row, col) VALUES (?, ?, ?)",
                               (unit_id, r, c))
            if cur.rowcount:
                conn.execute("INSERT INTO cube_sections(cube_id, position) VALUES (?, 0)", (cur.lastrowid,))


def create_unit(conn: sqlite3.Connection, name: str, rows: int, cols: int, x: int = 0, y: int = 0) -> int:
    with conn:
        _check_free(conn, {"x": x, "y": y, "rows": rows, "cols": cols})
        unit_id = conn.execute("INSERT INTO shelf_units(name, rows, cols, x, y) VALUES (?, ?, ?, ?, ?)",
                               (name, rows, cols, x, y)).lastrowid
        _fill_cubes(conn, unit_id, rows, cols)
    return unit_id


def update_unit(conn: sqlite3.Connection, unit_id: int, **values) -> bool:
    unit = _util.get(conn, "shelf_units", unit_id)
    if unit is None:
        return False
    with conn:
        _check_free(conn, {**unit, **values}, skip_id=unit_id)
        _util.update(conn, "shelf_units", unit_id, values, _UNIT_COLUMNS)
        if "rows" in values or "cols" in values:
            _fill_cubes(conn, unit_id, values.get("rows", unit["rows"]), values.get("cols", unit["cols"]))
    return True


def delete_unit(conn: sqlite3.Connection, unit_id: int) -> bool:
    return _util.delete(conn, "shelf_units", unit_id)


def update_cube(conn: sqlite3.Connection, cube_id: int, **values) -> bool:
    if _util.get(conn, "cubes", cube_id) is None:
        return False
    _util.update(conn, "cubes", cube_id, values, _CUBE_COLUMNS)
    return True


def add_section(conn: sqlite3.Connection, cube_id: int, name: str = "") -> int | None:
    """Add a divider: a new section at the right end of the cube."""
    if _util.get(conn, "cubes", cube_id) is None:
        return None
    (last,) = conn.execute("SELECT coalesce(max(position), -1) FROM cube_sections WHERE cube_id = ?",
                           (cube_id,)).fetchone()
    return _util.insert(conn, "cube_sections", {"cube_id": cube_id, "position": last + 1, "name": name})


def update_section(conn: sqlite3.Connection, section_id: int, **values) -> bool:
    if _util.get(conn, "cube_sections", section_id) is None:
        return False
    _util.update(conn, "cube_sections", section_id, values, _SECTION_COLUMNS)
    return True


def delete_section(conn: sqlite3.Connection, section_id: int) -> str:
    """Remove a divider. Its records merge into the neighbouring section, as they would on the
    shelf. Returns 'deleted', 'missing', or 'last' (a cube always keeps one section)."""
    section = _util.get(conn, "cube_sections", section_id)
    if section is None:
        return "missing"
    siblings = [r["id"] for r in conn.execute(
        "SELECT id FROM cube_sections WHERE cube_id = ? ORDER BY position, id", (section["cube_id"],))]
    if len(siblings) == 1:
        return "last"
    i = siblings.index(section_id)
    neighbour = siblings[i - 1] if i > 0 else siblings[1]
    with conn:
        conn.execute("UPDATE records SET section_id = ? WHERE section_id = ?", (neighbour, section_id))
        conn.execute("DELETE FROM cube_sections WHERE id = ?", (section_id,))
    return "deleted"


def place(conn: sqlite3.Connection, record_ids: list[int], section_id: int | None) -> list[int]:
    """Put records in a section (None = back to unsorted). Returns the ids that do not exist;
    nothing is moved unless all of them do."""
    marks = ",".join("?" * len(record_ids))
    found = {r[0] for r in conn.execute(f"SELECT id FROM records WHERE id IN ({marks})", record_ids)}
    missing = [i for i in record_ids if i not in found]
    if not missing:
        with conn:
            conn.execute(f"UPDATE records SET section_id = ? WHERE id IN ({marks})",
                         [section_id, *record_ids])
    return missing


def section_exists(conn: sqlite3.Connection, section_id: int) -> bool:
    return _util.get(conn, "cube_sections", section_id) is not None


# --- suggestions ------------------------------------------------------------------------------

def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _fold(text)))


_RANGE = re.compile(r"(?<![a-z0-9])([a-z0-9])\s*[-–—]\s*([a-z0-9])(?![a-z0-9])")


def _initial(artist: str) -> str:
    name = _fold(artist).strip()
    name = re.sub(r"^the\s+", "", name)
    match = re.search(r"[a-z0-9]", name)
    return match.group(0) if match else ""


def score(record: dict, labels: list[str]) -> tuple[int, list[str]]:
    """How well a record fits a place described by labels (unit, cube and section names and the
    cube description). A tag or style named in full scores 2, sharing a word with one scores 1,
    and the artist's initial inside a letter range like 'A–M' scores 1. Returns (score, reasons)."""
    text = " ".join(labels)
    words = _words(text)
    padded = " " + " ".join(re.findall(r"[a-z0-9]+", _fold(text))) + " "
    total, reasons = 0, []
    for term in dict.fromkeys([*record["tags"], *record["styles"]]):
        term_words = re.findall(r"[a-z0-9]+", _fold(term))
        if term_words and f" {' '.join(term_words)} " in padded:
            total += 2
            reasons.append(term)
        elif any(len(w) >= 3 and w in words for w in term_words):
            total += 1
            reasons.append(term)
    initial = _initial(record["artist"])
    for lo, hi in _RANGE.findall(_fold(text)):
        if initial and lo <= initial <= hi:
            total += 1
            reasons.append(f"{record['artist']} in {lo.upper()}–{hi.upper()}")
            break
    return total, reasons


def suggest(record: dict, places: list[dict]) -> dict | None:
    """The best-scoring section for a record, or None when nothing on the shelf matches it.
    Ties go to the first place in shelf order."""
    best = None
    for place in places:
        points, reasons = score(record, place["labels"])
        if points and (best is None or points > best["score"]):
            best = {"section_id": place["section_id"], "score": points, "reasons": reasons}
    return best


# --- read -------------------------------------------------------------------------------------

def cube_label(cube: dict) -> str:
    return cube["name"] or f"row {cube['row'] + 1}, cube {cube['col'] + 1}"


def layout(conn: sqlite3.Connection) -> dict:
    """The whole shelf with the owned records in each section, plus unsorted owned records with
    a suggested section each."""
    tags: dict[int, list[str]] = {}
    for row in conn.execute("SELECT rt.record_id, t.name FROM record_tags rt JOIN tags t ON t.id = rt.tag_id "
                            "ORDER BY t.name"):
        tags.setdefault(row[0], []).append(row[1])
    by_section: dict[int | None, list[dict]] = {}
    for row in conn.execute("SELECT id, artist, title, year, cover_url, styles, section_id FROM records "
                            "WHERE status = 'owned' ORDER BY artist COLLATE NOCASE, title COLLATE NOCASE"):
        record = dict(row)
        record["styles"] = json.loads(record["styles"]) if record["styles"] else []
        record["tags"] = tags.get(record["id"], [])
        by_section.setdefault(record.pop("section_id"), []).append(record)

    units = [dict(u) for u in conn.execute("SELECT * FROM shelf_units ORDER BY y, x, id")]
    cubes: dict[int, list[dict]] = {}
    for c in conn.execute("SELECT * FROM cubes ORDER BY row, col"):
        cubes.setdefault(c["unit_id"], []).append({**dict(c), "sections": []})
    cube_index = {c["id"]: c for cs in cubes.values() for c in cs}
    for s in conn.execute("SELECT * FROM cube_sections ORDER BY position, id"):
        cube_index[s["cube_id"]]["sections"].append(
            {"id": s["id"], "position": s["position"], "name": s["name"],
             "records": by_section.get(s["id"], [])})

    places = []
    for unit in units:
        unit["cubes"] = cubes.get(unit["id"], [])
        for cube in unit["cubes"]:
            for section in cube["sections"]:
                places.append({"section_id": section["id"],
                               "labels": [unit["name"], cube["name"], cube["description"], section["name"]]})
    unsorted = [{**r, "suggestion": suggest(r, places)} for r in by_section.get(None, [])]
    return {"units": units, "unsorted": unsorted}
