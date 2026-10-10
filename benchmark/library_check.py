"""Run the shipped key detector on the real-library audio kept in benchmark/audio and compare
with what the cache holds (previous Essentia result + database keys). No ground truth here."""
import json, sqlite3, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

def one(path):
    import essentia.standard as es
    from bpmkey import keydetect
    e = keydetect.detect(es.MonoLoader(filename=str(path), sampleRate=44100)())
    return e.index, e.scores.tolist()

if __name__ == "__main__":
    from bpmkey.camelot import camelot_to_key_index, key_index_to_camelot
    db = sqlite3.connect(ROOT.parent / "cache.sqlite")
    files = {}
    for f in (ROOT / "audio").iterdir():
        files[f.stem] = f
    rows = []
    for rid, pos, art, ti, ms in db.execute("select * from tracks"):
        if f"{rid}_{pos}" in files or (len(pos) == 0):
            pass
        stem = f"{rid}_{pos}"
        if stem not in files:
            continue
        ms = json.loads(ms)
        old = next((m["camelot"] for m in ms if m["origin"].startswith("essentia") and m["camelot"]), None)
        dbs = {m["origin"]: m["camelot"] for m in ms if not m["origin"].startswith("essentia") and m["camelot"]}
        rows.append((stem, art, ti, old, dbs, files[stem]))
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, [r[5] for r in rows]))
    out = []
    for (stem, art, ti, old, dbs, _), (idx, scores) in zip(rows, res):
        out.append({"stem": stem, "artist": art, "title": ti, "old": old, "new": key_index_to_camelot(idx),
                    "dbs": dbs, "scores": scores})
    (ROOT / "library_check.json").write_text(json.dumps(out))
    print(len(out), "tracks")
    print("old letters", Counter(o["old"][-1] for o in out if o["old"]), "new letters", Counter(o["new"][-1] for o in out))
    with_db = [o for o in out if o["dbs"]]
    for name in ("old", "new"):
        agree = sum(any(o[name] == v for v in o["dbs"].values()) for o in with_db)
        print(f"{name}: matches at least one database exactly in {agree}/{len(with_db)} tracks")
    for o in with_db[:60]:
        print(f"{o['artist'][:14]:14} {o['title'][:22]:22} old {o['old'] or '-':4} new {o['new']:4} dbs {o['dbs']}")
