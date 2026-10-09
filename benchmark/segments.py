"""Does listening longer / to other parts of the track help?  Discogs tracks only.

For each track and each key method, estimate the key from
  - one window (head / middle / tail) of 15, 30, 60, 120 s
  - the whole track
  - K evenly spaced windows of 30 s or 60 s, combined by (a) majority vote and
    (b) confidence-weighted vote
and score every configuration against the database labels.

    python benchmark/segments.py [--jobs 10]
Outputs: benchmark/segments_results.csv, benchmark/segments_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))
CACHE = ROOT / "seg_cache"
SR = 44100
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PROFILES = ["edmm", "bgate", "edma"]
SIZES = [15, 30, 60, 120]
MULTI = [(3, 30), (5, 30), (8, 30), (3, 60), (5, 60)]  # (windows, seconds each)


def window(y, where: str, secs: int):
    n = secs * SR
    if len(y) <= n:
        return y
    start = {"head": 0, "mid": (len(y) - n) // 2, "tail": len(y) - n}[where]
    return y[start:start + n]


def spread(y, k: int, secs: int):
    n = secs * SR
    if len(y) <= n:
        return [y]
    k = max(1, min(k, len(y) // n))  # non-overlapping windows only
    return [y[int(max(0, min(c - n / 2, len(y) - n))):][:n] for c in ((i + 0.5) / k * len(y) for i in range(k))]


def estimate(es, prof: str, y):
    k, s, strength = es.KeyExtractor(profileType=prof)(y)
    from methods import FLAT
    k = FLAT.get(k, k)
    return NOTES.index(k) + (12 if s == "minor" else 0), float(strength)


def vote(items, weighted: bool):
    tally = np.zeros(24)
    for idx, strength in items:
        tally[idx] += strength if weighted else 1.0
    return int(np.argmax(tally))


def name(i: int):
    return [NOTES[i % 12], "minor" if i >= 12 else "major"]


def analyse(audio: str) -> dict:
    cf = CACHE / (Path(audio).stem + ".json")
    if cf.exists():
        return json.loads(cf.read_text())
    import essentia.standard as es
    from methods import load
    y = load(str(ROOT / audio))
    out = {"duration": len(y) / SR}
    for prof in PROFILES:
        out[f"{prof} | whole track"] = name(estimate(es, prof, y)[0])
        for where in ("head", "mid", "tail"):
            for secs in SIZES:
                out[f"{prof} | {where} {secs}s"] = name(estimate(es, prof, window(y, where, secs))[0])
        for k, secs in MULTI:
            items = [estimate(es, prof, w) for w in spread(y, k, secs)]
            out[f"{prof} | {k}x{secs}s majority"] = name(vote(items, False))
            out[f"{prof} | {k}x{secs}s weighted"] = name(vote(items, True))
    out |= current_model(y)
    CACHE.mkdir(exist_ok=True)
    cf.write_text(json.dumps(out))
    return out


def current_model(y) -> dict:
    """The project's detector (learned model + bgate vote) on selected windows."""
    import essentia.standard as es
    import librosa
    from bpmkey import keymodel

    def run(parts):
        lp = np.mean([keymodel.log_probs(librosa.resample(p, orig_sr=SR, target_sr=keymodel.SR)) for p in parts], axis=0)
        bg = vote([estimate(es, "bgate", p) for p in parts], True)
        return name(int(np.argmax(keymodel.fuse(lp, bg))))

    out = {"current | whole track": name(int(np.argmax(keymodel.fuse(
        keymodel.log_probs(librosa.resample(y, orig_sr=SR, target_sr=keymodel.SR)),
        estimate(es, "bgate", y)[0]))))}
    for where in ("head", "mid", "tail"):
        out[f"current | {where} 60s"] = run([window(y, where, 60)])
    out["current | 5x30s"] = run(spread(y, 5, 30))
    out["current | 5x60s"] = run(spread(y, 5, 60))
    return out


def main() -> None:
    import mir_eval
    import pandas as pd
    from run import camelot_name, camelot_of, mixable

    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    a = ap.parse_args()
    labels = json.loads((ROOT / "labels.json").read_text())
    tracks = [r for r in labels.values() if r.get("audio") and (r["label"] or r["weak_label"])]
    with ProcessPoolExecutor(a.jobs) as ex:
        res = list(ex.map(analyse, [t["audio"] for t in tracks]))
    configs = [c for c in res[0] if c != "duration"]

    rng = np.random.default_rng(0)
    rows = []
    subsets = {
        "all 43 labelled tracks": lambda t, r: True,
        "tracks >= 150 s only": lambda t, r: r["duration"] >= 150,
    }
    for sname, keep in subsets.items():
        idx = [i for i, (t, r) in enumerate(zip(tracks, res)) if keep(t, r)]
        for c in configs:
            sc, ex_, mx = [], [], []
            for i in idx:
                truth = tracks[i]["label"] or tracks[i]["weak_label"]
                est = res[i][c]
                ref = camelot_name(truth)
                sc.append(mir_eval.key.weighted_score(f"{ref[0]} {ref[1]}", f"{est[0]} {est[1]}"))
                ec = camelot_of(*est)
                ex_.append(ec == truth), mx.append(mixable(truth, ec))
            sc = np.array(sc)
            boots = [rng.choice(sc, len(sc)).mean() for _ in range(1000)]
            method, setting = c.split(" | ")
            rows.append({"subset": sname, "n": len(idx), "method": method, "setting": setting,
                         "weighted": sc.mean(), "ci_lo": np.percentile(boots, 2.5),
                         "ci_hi": np.percentile(boots, 97.5), "exact_%": 100 * np.mean(ex_),
                         "mixable_%": 100 * np.mean(mx)})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "segments_results.csv", index=False)
    with open(ROOT / "segments_report.md", "w") as f:
        f.write("# Listening longer / to different parts of the track (Discogs tracks)\n\n"
                "Ground truth = online-database keys (weak labels, not human). "
                "Windows longer than the track use the whole track.\n\n")
        for sname, g in df.groupby("subset", sort=False):
            f.write(f"## {sname} (n={g['n'].iloc[0]})\n\n")
            for method, gm in g.groupby("method", sort=False):
                f.write(f"### {method}\n\n{gm.drop(columns=['subset', 'n', 'method']).round(3).sort_values('weighted', ascending=False).to_markdown(index=False)}\n\n")
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
