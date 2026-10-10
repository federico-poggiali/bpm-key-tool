"""Audio analysis behind one swappable interface: analyze(path) -> dict."""
from pathlib import Path

ENGINE = "bpmkey-essentia"


def alternate_bpm(bpm: float) -> float:
    """The likely half/double-tempo reading: halve fast values, double slow ones."""
    return round(bpm / 2 if bpm >= 100 else bpm * 2, 1)


def analyze(path: Path | str) -> dict:
    from bpmkey.analyze import analyze_file

    m = analyze_file(path)
    bpm_alt = alternate_bpm(m.bpm) if m.bpm else None
    return {
        "bpm": m.bpm,
        "key": m.raw_key,
        "camelot_key": m.camelot,
        "confidence": m.confidence,
        "raw": {"engine": ENGINE, "bpm": m.bpm, "bpm_alt": bpm_alt, "key_scores": m.key_scores},
    }
