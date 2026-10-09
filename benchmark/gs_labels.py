"""Convert GiantSteps Key annotations + downloaded mp3s into benchmark/gs_labels.json."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from bpmkey.camelot import to_camelot

base = ROOT / "gs" / "giantsteps-key-dataset"
out, skipped = {}, 0
for k in sorted((base / "annotations" / "key").glob("*.key")):
    text = k.read_text().strip()
    code = None if "/" in text or text in ("", "-") else to_camelot(text)
    mp3 = base / "audio" / (k.stem + ".mp3")
    if not code or not mp3.exists() or mp3.stat().st_size < 10000:
        skipped += 1
        continue
    out[k.stem] = {"artist": "", "title": k.stem, "label": code, "weak_label": None,
                   "audio": str(mp3.relative_to(ROOT))}
(ROOT / "gs_labels.json").write_text(json.dumps(out, indent=1))
print(f"{len(out)} tracks, {skipped} skipped")
