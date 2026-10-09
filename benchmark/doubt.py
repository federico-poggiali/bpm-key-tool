"""Calibrate when to fall back from edmm to bgate, using GiantSteps (human labels)."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parent))
NOTES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
OUT = ROOT / "doubt.json"

def one(item):
    audio = item
    import essentia.standard as es
    from methods import load, FLAT
    y = load(str(ROOT / audio))
    r = []
    for p in ("edmm", "bgate"):
        k, s, st = es.KeyExtractor(profileType=p)(y)
        r.append((NOTES.index(FLAT.get(k, k)) + (12 if s == "minor" else 0), float(st)))
    return r

if __name__ == "__main__":
    from bpmkey.camelot import camelot_to_key_index
    import mir_eval
    labels = list(json.loads((ROOT / "gs_labels.json").read_text()).values())
    with ProcessPoolExecutor(10) as ex:
        res = list(ex.map(one, [l["audio"] for l in labels], chunksize=8))
    truth = np.array([camelot_to_key_index(l["label"]) for l in labels])
    OUT.write_text(json.dumps({"truth": truth.tolist(), "res": res}))
