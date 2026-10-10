"""Cache mean chroma (12) per GiantSteps clip -> benchmark/chroma.npy (row order = profiles.json ids)."""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parent))

def one(audio):
    from methods import load, _trim
    from bpmkey.keychroma import mean_chroma
    return mean_chroma(_trim(load(str(ROOT / audio))))

if __name__ == "__main__":
    labels = json.loads((ROOT / "gs_labels.json").read_text())
    with ProcessPoolExecutor(10) as ex:
        C = list(ex.map(one, [l["audio"] for l in labels.values()], chunksize=8))
    np.save(ROOT / "chroma.npy", np.array(C)); print(np.array(C).shape)
