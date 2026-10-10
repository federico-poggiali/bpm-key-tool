"""Match audio files in audio/<release_id>/ to a record's tracks. Never guesses silently."""
import re
from difflib import SequenceMatcher
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aif", ".aiff", ".m4a", ".ogg"}
TITLE_THRESHOLD = 0.8
TITLE_MARGIN = 0.05

_POSITION = re.compile(r"^\s*([A-Za-z]{1,2}\d{1,2}|\d{1,2}-\d{1,2}|\d{1,3})(?=[\s._\-)]|$)")


def normalize_position(position: str) -> str:
    return re.sub(r"\d+", lambda m: str(int(m.group())), position.strip().upper())


def file_position(stem: str) -> str | None:
    m = _POSITION.match(stem)
    return normalize_position(m.group(1)) if m else None


def _clean(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _title_part(stem: str) -> str:
    m = _POSITION.match(stem)
    return _clean(stem[m.end():] if m else stem)


def find_audio_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and not p.name.startswith(".")
                  and p.suffix.lower() in AUDIO_EXTENSIONS)


def match_files(files: list[Path], tracks: list[dict]) -> dict:
    matched: list[dict] = []
    unmatched_files: list[dict] = []
    free_tracks = {t["id"]: t for t in tracks}
    files_left: list[Path] = []

    # 1. By position in the filename ("A1 - Title.wav"); ambiguity on either side is skipped.
    by_position: dict[str, list[dict]] = {}
    for t in tracks:
        if t["position"]:
            by_position.setdefault(normalize_position(t["position"]), []).append(t)
    claimed: dict[str, list[Path]] = {}
    for f in files:
        pos = file_position(f.stem)
        if pos is not None:
            claimed.setdefault(pos, []).append(f)
    for f in files:
        pos = file_position(f.stem)
        candidates = by_position.get(pos, []) if pos else []
        if pos and len(claimed[pos]) > 1:
            unmatched_files.append({"file": f.name, "reason": f"several files claim position {pos}"})
        elif len(candidates) == 1 and candidates[0]["id"] in free_tracks:
            t = free_tracks.pop(candidates[0]["id"])
            matched.append({"track_id": t["id"], "position": t["position"], "file": f.name,
                            "method": "position", "score": 1.0})
        else:
            files_left.append(f)

    # 2. Fuzzy title for what is left, only when the best candidate is clearly ahead.
    proposals = []
    for f in files_left:
        title = _title_part(f.stem)
        scored = sorted(
            ((SequenceMatcher(None, title, _clean(t["title"])).ratio(), t["id"])
             for t in free_tracks.values()), reverse=True)
        if not scored or scored[0][0] < TITLE_THRESHOLD:
            unmatched_files.append({"file": f.name, "reason": "no track matches this file"})
        elif len(scored) > 1 and scored[0][0] - scored[1][0] < TITLE_MARGIN:
            unmatched_files.append({"file": f.name, "reason": "title matches several tracks"})
        else:
            proposals.append((scored[0][0], f, scored[0][1]))
    for score, f, track_id in sorted(proposals, key=lambda p: -p[0]):
        if track_id in free_tracks:
            t = free_tracks.pop(track_id)
            matched.append({"track_id": t["id"], "position": t["position"], "file": f.name,
                            "method": "title", "score": round(score, 2)})
        else:
            unmatched_files.append({"file": f.name, "reason": "its best track is taken by another file"})

    return {
        "matched": sorted(matched, key=lambda m: m["track_id"]),
        "unmatched_files": sorted(unmatched_files, key=lambda u: u["file"]),
        "unmatched_tracks": [{"track_id": t["id"], "position": t["position"], "title": t["title"]}
                             for t in free_tracks.values()],
    }
