"""The 'analysis' job: match audio to tracks, analyze each match, store the results."""
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from app import config
from app.analysis import engine
from app.analysis.matching import find_audio_files, match_files
from app.db import records, tracks

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


def make_handler(analyze: Callable[[Path], dict] = engine.analyze,
                 audio_dir: Path | None = None) -> Callable[[sqlite3.Connection, dict], dict]:
    def handler(conn: sqlite3.Connection, job: dict) -> dict:
        record = records.get(conn, job["record_id"])
        if record is None:
            raise ValueError("record no longer exists")
        folder = audio_folder(record, audio_dir)
        if folder is None or not find_audio_files(folder):
            raise FileNotFoundError(f"no audio files found in {folder or 'audio folder'}")
        report = match_report(conn, record["id"], audio_dir)
        analyzed, errors = [], []
        for m in report["matched"]:
            path = folder / m["file"]
            try:
                result = analyze(path)
            except Exception as exc:
                errors.append({"file": m["file"], "error": f"{type(exc).__name__}: {exc}"})
                continue
            tracks.update(
                conn, m["track_id"], bpm=result["bpm"], key=result["key"],
                camelot_key=result["camelot_key"], confidence=result["confidence"],
                analysis_raw=result["raw"], audio_path=str(path),
                analyzed_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
            analyzed.append(m["track_id"])
        return {**report, "analyzed_track_ids": analyzed, "errors": errors}

    return handler
