"""Cache KeyExtractor (key index, strength) for several profiles on every GiantSteps clip.

    python benchmark/profiles.py   ->  benchmark/profiles.json  (used by benchmark/evaluate.py)
"""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parent))
PROFILES = ("edmm", "edma", "bgate", "krumhansl", "temperley", "shaath", "braw")
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def one(audio):
    import essentia.standard as es
    from methods import load, _trim, FLAT
    y = _trim(load(str(ROOT / audio)))
    out = {}
    for p in PROFILES:
        k, s, st = es.KeyExtractor(profileType=p)(y)
        out[p] = [NOTES.index(FLAT.get(k, k)) + (12 if s == "minor" else 0), float(st)]
    return out


if __name__ == "__main__":
    from bpmkey.camelot import camelot_to_key_index
    labels = json.loads((ROOT / "gs_labels.json").read_text())
    with ProcessPoolExecutor(10) as ex:
        res = list(ex.map(one, [l["audio"] for l in labels.values()], chunksize=8))
    (ROOT / "profiles.json").write_text(json.dumps({
        "ids": list(labels), "truth": [camelot_to_key_index(l["label"]) for l in labels.values()],
        "res": res}))
    print(len(res), "tracks")
