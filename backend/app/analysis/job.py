"""The 'analysis' job: look BPM/key up from the Discogs link; local audio files override.

Results are stored as proposals; the owner validates them onto the tracks (see validate)."""
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from app import config
from app.analysis import engine, lookup
from app.analysis.matching import find_audio_files, match_files
from app.db import proposals, records, tracks
from app.discogs import DiscogsClient

JOB_TYPE = "analysis"


def audio_folder(record: dict, audio_dir: Path | None = None) -> Path | None:
    if record["discogs_release_id"] is None:
        return None
    return (audio_dir or config.AUDIO_DIR) / str(record["discogs_release_id"])


def match_report(conn: sqlite3.Connection, record_id: int, audio_dir: Path | None = None) -> dict:
    record = records.get(conn, record_id)
    folder = audio_folder(record, audio_dir)
    files = find_audio_files(folder) if folder else []
    report = match_files(files, tracks.list_for_record(conn, record_id))
    return {"folder": str(folder) if folder else None, **report}


def _store(conn: sqlite3.Connection, track_id: int, result: dict, audio_path: Path | None) -> None:
    """Keep an analysis result as a proposal; nothing reaches the track until it is validated."""
    proposals.put(conn, track_id, bpm=result["bpm"], key=result["key"], camelot_key=result["camelot_key"],
                  confidence=result["confidence"], analysis_raw=result["raw"],
                  audio_path=str(audio_path) if audio_path else None,
                  proposed_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))


def validate(conn: sqlite3.Connection, track_ids: list[int], overwrite_manual: bool = False) -> None:
    """Copy these tracks' proposals onto them. A hand-entered value is kept unless overwrite_manual."""
    for track_id in track_ids:
        p = proposals.get(conn, track_id)
        current = tracks.get(conn, track_id)
        values = {"analysis_raw": p["analysis_raw"], "analyzed_at": p["proposed_at"]}
        if p["bpm"] is not None and (overwrite_manual or not current["bpm_manual"]):
            values.update(bpm=p["bpm"], bpm_manual=0)
        if p["camelot_key"] is not None and (overwrite_manual or not current["key_manual"]):
            # confidence describes the analysed key, so it only travels with it
            values.update(key=p["key"], camelot_key=p["camelot_key"], confidence=p["confidence"],
                          key_manual=0)
        if p["audio_path"]:
            values["audio_path"] = p["audio_path"]
        tracks.update(conn, track_id, **values)
    proposals.delete(conn, track_ids)


def make_handler(
    discogs_factory: Callable[[], DiscogsClient],
    lookup_fn: Callable[[dict, list[dict], dict], dict[int, dict]] = lookup.lookup_tracks,
    analyze: Callable[[Path], dict] = engine.analyze,
    audio_dir: Path | None = None,
) -> Callable[[sqlite3.Connection, dict], dict]:
    def handler(conn: sqlite3.Connection, job: dict) -> dict:
        record = records.get(conn, job["record_id"])
        if record is None:
            raise ValueError("record no longer exists")
        if record["discogs_release_id"] is None:
            raise ValueError("record has no Discogs release id")
        track_rows = tracks.list_for_record(conn, record["id"])
        selected = (job.get("params") or {}).get("track_ids")
        if selected is not None:
            track_rows = [t for t in track_rows if t["id"] in set(selected)]
        errors: list[dict] = []

        # 1. From the Discogs link: online databases, then audio bpmkey finds itself.
        release = discogs_factory().release(record["discogs_release_id"])
        found = lookup_fn(record, track_rows, release)
        for track_id, result in found.items():
            _store(conn, track_id, result, None)

        # 2. Optional: files you dropped in audio/<release_id>/ override the lookup.
        report = match_report(conn, record["id"], audio_dir)
        from_files: list[int] = []
        folder = audio_folder(record, audio_dir)
        for m in report["matched"]:
            if selected is not None and m["track_id"] not in selected:
                continue
            path = folder / m["file"]
            try:
                result = analyze(path)
            except Exception as exc:
                errors.append({"file": m["file"], "error": f"{type(exc).__name__}: {exc}"})
                continue
            _store(conn, m["track_id"], result, path)
            from_files.append(m["track_id"])

        got_data = set(found) | set(from_files)
        return {
            "looked_up_track_ids": sorted(found),
            "from_audio_files_track_ids": from_files,
            "no_data_track_ids": [t["id"] for t in track_rows if t["id"] not in got_data],
            "audio_match": report,
            "errors": errors,
        }

    return handler
