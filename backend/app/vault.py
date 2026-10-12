"""Generate the Obsidian vault from the database. The DB is the only source of truth: every file here
is regenerated on each sync and edits made in Obsidian are discarded (never synced back).

CLI: python -m app.vault
"""
import json
import logging
import os
import re
import sqlite3
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app import config
from app.db import connect, queries

log = logging.getLogger(__name__)

MARKER = "generated_by: vinyl-second-brain"
RECORDS_SUBDIR = "Records"
EXAMPLES_FILE = "Dataview Examples.md"
_ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f#^\[\]]')

BANNER = ("> [!warning] Generated file, do not edit\n"
          "> This note is rebuilt from the Vinyl Second-Brain database on every sync. "
          "Changes made here are overwritten. Edit the record in the app instead.\n")

DATAVIEW_EXAMPLES = '''# Dataview examples

Generated file, do not edit. These queries read the frontmatter of the notes in `Records/`
(the Dataview plugin must be enabled).

## Records with a track between 120 and 128 BPM

```dataview
TABLE artist, title, bpm_min, bpm_max, camelot_keys
FROM "Records"
WHERE status = "owned" AND bpm_min <= 128 AND bpm_max >= 120
SORT bpm_min ASC
```

## Records with a track in a given key (Camelot 8A = A minor)

```dataview
TABLE artist, title, keys, camelot_keys
FROM "Records"
WHERE contains(camelot_keys, "8A")
SORT artist ASC
```

## Records by style

```dataview
TABLE artist, title, label, styles
FROM "Records"
WHERE contains(styles, "Dub Techno")
SORT year DESC
```

## Records by tag

```dataview
TABLE artist, title, year, tags
FROM #house
SORT year DESC
```

## Wantlist and considering

```dataview
TABLE artist, title, label, status
FROM "Records"
WHERE status != "owned"
SORT status ASC, artist ASC
```
'''


@dataclass
class SyncResult:
    written: int = 0
    skipped: int = 0
    deleted: int = 0
    synced_at: str = ""


def _safe(text: str) -> str:
    return re.sub(r"\s+", " ", _ILLEGAL.sub("-", text)).strip(" .")


def filename_for(record: dict) -> str:
    ident = record["discogs_release_id"] or f"local-{record['id']}"
    stem = _safe(f"{record['artist']} - {record['title']}")[:120].rstrip(" .-")
    return f"{stem} ({ident}).md"


def _yaml(value) -> str:
    """JSON is valid YAML, so strings, numbers, lists and null all serialise safely."""
    return json.dumps(value, ensure_ascii=False)


def _cell(text) -> str:
    return "" if text is None else str(text).replace("|", "\\|").replace("\n", " ").strip()


def _num(value: float | None) -> str:
    return "" if value is None else f"{value:g}"


def render_record(record: dict) -> str:
    tracks = record["tracks"]
    bpms = [t["bpm"] for t in tracks if t["bpm"] is not None]
    keys = sorted({t["key"] for t in tracks if t["key"]})
    camelot = sorted({t["camelot_key"] for t in tracks if t["camelot_key"]},
                     key=lambda c: (int(c[:-1]), c[-1]))
    front = [
        ("discogs_id", record["discogs_release_id"]), ("artist", record["artist"]),
        ("title", record["title"]), ("label", record["label"]), ("catno", record["catno"]),
        ("year", record["year"]),
        ("format", record["format"]), ("status", record["status"]), ("styles", record["styles"]),
        ("tags", record["tags"]),
        ("bpm_min", min(bpms) if bpms else None), ("bpm_max", max(bpms) if bpms else None),
        ("keys", keys), ("camelot_keys", camelot),
    ]
    lines = ["---", MARKER] + [f"{k}: {_yaml(v)}" for k, v in front] + ["---", "", BANNER,
             f"# {record['artist']} - {record['title']}", ""]
    meta = [str(x) for x in (record["label"], record["year"], record["format"]) if x]
    if meta:
        lines += [" · ".join(meta), ""]
    if record["cover_url"]:
        lines += [f"![cover]({record['cover_url']})", ""]

    lines += ["## Tracklist", "", "| Pos | Title | BPM | Key | Confidence |",
              "| --- | --- | --- | --- | --- |"]
    for t in tracks:
        bpm = _num(t["bpm"]) + (" (manual)" if t["bpm"] is not None and t["bpm_manual"] else "")
        key = " · ".join(x for x in (t["key"], t["camelot_key"]) if x)
        if key and t["key_manual"]:
            key += " (manual)"
        conf = "" if t["confidence"] is None else f"{t['confidence']:.0%}"
        title = _cell(t["title"])
        if t["artist"] and t["artist"] != record["artist"]:
            title += f" ({_cell(t['artist'])})"
        lines.append(f"| {_cell(t['position'])} | {title} | {bpm} | {_cell(key)} | {conf} |")
    lines.append("")

    if record["notes"]:
        lines += ["## Notes", ""]
        for n in record["notes"]:
            lines += [f"### {n['type']}", "", n["body"].strip(), ""]
    with_notes = [t for t in tracks if t["notes"]]
    if with_notes:
        lines += ["## Track notes", ""]
        for t in with_notes:
            lines += [f"### {t['position']} {t['title']}".replace("  ", " "), ""]
            for n in t["notes"]:
                lines += [f"**{n['type']}**", "", n["body"].strip(), ""]
    return "\n".join(lines).rstrip() + "\n"


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".vault-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return True


def _is_ours(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8") as f:
            return MARKER in f.read(400)
    except OSError:
        return False


def sync_vault(conn: sqlite3.Connection, vault_dir: Path | None = None) -> SyncResult:
    vault = Path(vault_dir or config.VAULT_DIR)
    records_dir = vault / RECORDS_SUBDIR
    result = SyncResult()
    expected: set[str] = set()
    ids = [r[0] for r in conn.execute("SELECT id FROM records ORDER BY id")]
    for record_id in ids:
        record = queries.record_detail(conn, record_id)
        name = filename_for(record)
        expected.add(name)
        if _write_if_changed(records_dir / name, render_record(record)):
            result.written += 1
        else:
            result.skipped += 1
    if _write_if_changed(vault / EXAMPLES_FILE, DATAVIEW_EXAMPLES):
        result.written += 1
    else:
        result.skipped += 1
    if records_dir.is_dir():  # only generated files are removed; anything else is left alone
        for path in records_dir.glob("*.md"):
            if path.name not in expected and _is_ours(path):
                path.unlink()
                result.deleted += 1
    result.synced_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return result


class VaultSyncer:
    """Debounced background sync: request() after any write; one sync runs once writes go quiet."""

    def __init__(self, vault_dir: Path | None = None, delay: float = 2.0):
        self.vault_dir = Path(vault_dir or config.VAULT_DIR)
        self.delay = delay
        self.last_result: dict | None = None
        self.last_error: str | None = None
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()  # guards the timer
        self._run_lock = threading.Lock()  # one sync at a time

    def request(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.delay, self.run_now)
            self._timer.daemon = True
            self._timer.start()

    def run_now(self) -> dict:
        with self._run_lock:
            conn = connect()
            try:
                self.last_result = asdict(sync_vault(conn, self.vault_dir))
                self.last_error = None
            except Exception as exc:
                log.exception("vault sync failed")
                self.last_error = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                conn.close()
            log.info("vault synced", extra={"vault": self.last_result})
            return self.last_result

    def stop(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()


def main() -> None:
    conn = connect()
    result = sync_vault(conn)
    conn.close()
    print(f"vault {config.VAULT_DIR}: {result.written} written, {result.skipped} unchanged, "
          f"{result.deleted} deleted")


if __name__ == "__main__":
    main()
