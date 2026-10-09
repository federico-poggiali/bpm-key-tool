"""Run every method on the collected tracks, score with MIREX weights, write results.

    python benchmark/run.py [--jobs 4] [--methods substr,substr]
Outputs: benchmark/results.csv, benchmark/report.md (per-track cache in benchmark/cache/).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))

CACHE = ROOT / "cache"
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def camelot_name(code: str) -> tuple[str, str]:
    from bpmkey.camelot import camelot_to_key_index
    i = camelot_to_key_index(code)
    return NOTES[i % 12], "minor" if i >= 12 else "major"


def camelot_of(tonic: str, mode: str) -> str:
    from bpmkey.camelot import key_index_to_camelot
    return key_index_to_camelot(NOTES.index(tonic) + (12 if mode == "minor" else 0))


def cache_file(method: str, audio: str) -> Path:
    safe = "".join(c if c.isalnum() else "_" for c in method)
    return CACHE / f"{safe}__{Path(audio).stem}.json"


def work(args):
    method, audio = args
    from methods import registry
    cf = cache_file(method, audio)
    if cf.exists():
        return json.loads(cf.read_text())
    t0 = time.time()
    try:
        tonic, mode = registry()[method](str(ROOT / audio))
        out = {"method": method, "audio": audio, "est": [tonic, mode], "sec": time.time() - t0}
    except Exception as e:
        out = {"method": method, "audio": audio, "error": f"{type(e).__name__}: {e}",
               "trace": traceback.format_exc()[-400:], "sec": time.time() - t0}
    CACHE.mkdir(exist_ok=True)
    cf.write_text(json.dumps(out))
    return out


def mixable(ref: str, est: str) -> bool:
    """Same key, relative major/minor, or one step around the Camelot wheel."""
    rn, rl, en, el = int(ref[:-1]), ref[-1], int(est[:-1]), est[-1]
    if rl == el:
        return (rn - en) % 12 in (0, 1, 11)
    return rn == en


def main() -> None:
    import mir_eval
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--methods", default="")
    ap.add_argument("--dataset", choices=["discogs", "giantsteps"], default="discogs")
    ap.add_argument("--limit", type=int, default=0, help="use only the first N tracks")
    a = ap.parse_args()
    tag = ("" if a.dataset == "discogs" else "_giantsteps") + (f"_first{a.limit}" if a.limit else "")

    from methods import NOT_RUN, registry
    labels = json.loads((ROOT / ("labels.json" if a.dataset == "discogs" else "gs_labels.json")).read_text())
    tracks = [r for r in labels.values() if r.get("audio") and (r["label"] or r["weak_label"])]
    if a.limit:
        tracks = tracks[:a.limit]
    names = [m for m in registry() if not a.methods or any(s.lower() in m.lower() for s in a.methods.split(","))]
    jobs = [(m, t["audio"]) for m in names for t in tracks]
    print(f"{len(tracks)} tracks x {len(names)} methods = {len(jobs)} jobs", flush=True)

    out = {}
    with ProcessPoolExecutor(a.jobs) as ex:
        for i, r in enumerate(ex.map(work, jobs, chunksize=1), 1):
            out[(r["method"], r["audio"])] = r
            if i % 25 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)

    rng = np.random.default_rng(0)
    rows = []
    for subset, pick in (("agreed (2 DBs)", lambda t: t["label"]), ("all labels", lambda t: t["label"] or t["weak_label"])):
        ts = [t for t in tracks if pick(t)]
        for m in names:
            sc, ex_, mx, secs, fails = [], [], [], [], 0
            for t in ts:
                r = out[(m, t["audio"])]
                if "est" not in r:
                    fails += 1
                    sc.append(0.0), ex_.append(0), mx.append(0)
                    continue
                ref, est = camelot_name(pick(t)), tuple(r["est"])
                sc.append(mir_eval.key.weighted_score(f"{ref[0]} {ref[1]}", f"{est[0]} {est[1]}"))
                ec = camelot_of(*est)
                ex_.append(int(ec == pick(t))), mx.append(int(mixable(pick(t), ec))), secs.append(r["sec"])
            sc = np.array(sc)
            boots = [rng.choice(sc, len(sc)).mean() for _ in range(1000)]
            rows.append({"subset": subset, "n": len(ts), "method": m, "weighted": sc.mean(),
                         "ci_lo": np.percentile(boots, 2.5), "ci_hi": np.percentile(boots, 97.5),
                         "exact_%": 100 * np.mean(ex_), "mixable_%": 100 * np.mean(mx),
                         "sec_per_track": np.mean(secs) if secs else float("nan"), "failed": fails})
    import pandas as pd
    df = pd.DataFrame(rows).sort_values(["subset", "weighted"], ascending=[True, False])
    df.to_csv(ROOT / f"results{tag}.csv", index=False)
    with open(ROOT / f"report{tag}.md", "w") as f:
        gs = a.dataset == "giantsteps"
        f.write("# Key-detection benchmark\n\n" + (
            "GiantSteps Key: Beatport previews with user-corrected human labels"
            + (f" (first {a.limit} clips)" if a.limit else "") + ".\n\n" if gs else
            "Ground truth = keys from online databases (GetSongBPM, AcousticBrainz), NOT human labels. "
            "'agreed' = two databases gave the same key; 'all labels' also includes tracks with a "
            "single database key.\n\n"))
        for subset, g in df.groupby("subset", sort=False):
            if gs and subset != "agreed (2 DBs)":
                continue  # both subsets are identical for human-labelled data
            title = "Human labels" if gs else subset
            f.write(f"## {title} (n={g['n'].iloc[0]})\n\n{g.drop(columns=['subset', 'n']).round(3).to_markdown(index=False)}\n\n")
        f.write("## Not run\n\n" + "\n".join(f"- {k}: {v}" for k, v in NOT_RUN.items()) + "\n")
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
