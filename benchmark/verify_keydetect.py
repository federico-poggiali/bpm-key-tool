"""Check bpmkey.keydetect (the shipped detector) on GiantSteps."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

def one(a):
    import essentia.standard as es
    from bpmkey import keydetect
    e = keydetect.detect(es.MonoLoader(filename=str(ROOT / a), sampleRate=44100)())
    return e.index, e.source, e.in_doubt

if __name__ == "__main__":
    from bpmkey.camelot import camelot_to_key_index
    L = list(json.load(open(ROOT / "gs_labels.json")).values())
    with ProcessPoolExecutor(10) as ex:
        r = list(ex.map(one, [l["audio"] for l in L], chunksize=8))
    t = np.array([camelot_to_key_index(l["label"]) for l in L])
    i = np.array([x[0] for x in r]); d = np.array([x[2] for x in r])
    print(f"exact {np.mean(i == t):.3f}  in doubt {d.mean():.2f}  acc when doubtful {np.mean((i == t)[d]):.2f}  "
          f"backup used {sum(x[1] == 'bgate' for x in r)}")
