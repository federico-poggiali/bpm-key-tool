"""Check bpmkey.keydetect (the shipped detector) on GiantSteps end to end.

In-sample for the committee weights (they were fit on these clips), so expect numbers a little
above the cross-validated ones from keymodel_fit.py; this verifies the production path matches.
"""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent)); sys.path.insert(0, str(ROOT))

def one(a):
    import essentia.standard as es
    from bpmkey import keydetect
    e = keydetect.detect(es.MonoLoader(filename=str(ROOT / a), sampleRate=44100)())
    return e.index, e.source, e.in_doubt, e.confidence

if __name__ == "__main__":
    from bpmkey.camelot import camelot_to_key_index
    from keymodel_fit import mirex
    L = list(json.load(open(ROOT / "gs_labels.json")).values())
    with ProcessPoolExecutor(10) as ex:
        r = list(ex.map(one, [l["audio"] for l in L], chunksize=8))
    t = np.array([camelot_to_key_index(l["label"]) for l in L])
    i = np.array([x[0] for x in r]); d = np.array([x[2] for x in r]); c = np.array([x[3] for x in r])
    ok = i == t
    print(f"exact {ok.mean():.3f}  MIREX {mirex(i, t):.3f}  major recall {ok[t < 12].mean():.2f}  "
          f"minor recall {ok[t >= 12].mean():.2f}  predicted major {(i < 12).mean():.2f}")
    print(f"in doubt {d.mean():.2f}  acc when doubtful {ok[d].mean():.2f}  acc otherwise {ok[~d].mean():.2f}  "
          f"mean confidence {c.mean():.2f}  sources {sorted({x[1] for x in r})}")
