"""Simulate database hints on GiantSteps to compare ways of combining them with the audio.

GiantSteps has no database keys, so each database is simulated: with chance `r` it reports the
true key, otherwise a wrong one (half the time a relative/parallel/fifth neighbour, half uniform).
The audio posteriors are the cross-validated ones, so nothing here sees its own training labels.
    python benchmark/db_sim.py
"""
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parent))
from keymodel_fit import load, cv_probs, report, show, kc  # noqa: E402
from bpmkey import keydetect, reconcile  # noqa: E402

COVERAGE = {"getsongbpm": 0.5, "acousticbrainz": 0.7}  # share of tracks each database has a key for


def draw(truth, r, rng):
    if rng.random() < r:
        return truth
    near = np.flatnonzero(kc.relations(truth)[2:].sum(0))
    if rng.random() < reconcile.NEIGHBOUR_SHARE:
        return int(rng.choice(near))
    return int(rng.choice([k for k in range(24) if k != truth]))


def combine(logp, hints, rule):
    s = logp.copy()
    for origin, d in hints.items():
        if rule == "old":
            s[d] += {"getsongbpm": 1.0, "acousticbrainz": 0.5}[origin]
        elif rule == "bayes":
            s += reconcile.db_log_likelihood(d, reconcile.DB_RELIABILITY[origin])
    return s


if __name__ == "__main__":
    t, res = load(); C = np.load(ROOT / "chroma.npy")
    votes = [{p: tuple(r[p]) for p in kc.ALL_PROFILES} for r in res]
    X = np.array([kc.features(v, kc.SHIPPED_PROFILES, C[i]) for i, v in enumerate(votes)])
    new = cv_probs(X, t, kc.SHIPPED_LAMBDA, seeds=(0,))[0]
    new[:, :12] *= np.exp(keydetect.MODE_PRIOR_SHIFT); new /= new.sum(1, keepdims=True)  # as shipped
    legacy = np.array([kc.legacy_probs(v) for v in votes])
    for scenario, true_r in (("databases as good as assumed (0.5 / 0.35)", {"getsongbpm": 0.5, "acousticbrainz": 0.35}),
                             ("databases better (0.7 / 0.5)", {"getsongbpm": 0.7, "acousticbrainz": 0.5}),
                             ("databases worse (0.3 / 0.2)", {"getsongbpm": 0.3, "acousticbrainz": 0.2})):
        rng = np.random.default_rng(7)
        hints = [{o: draw(int(t[i]), true_r[o], rng) for o in COVERAGE if rng.random() < COVERAGE[o]}
                 for i in range(len(t))]
        print(f"\n== {scenario}; {np.mean([bool(h) for h in hints]):.0%} of tracks have a database key")
        rows = []
        for name, audio, rule in (("legacy audio, no databases", legacy, None),
                                  ("legacy audio + old fixed weights", legacy, "old"),
                                  ("committee audio, no databases", new, None),
                                  ("committee audio + old fixed weights", new, "old"),
                                  ("committee audio + reliability model", new, "bayes")):
            S = np.array([combine(np.log(audio[i]), h, rule) for i, h in enumerate(hints)])
            P = np.exp(S - S.max(1, keepdims=True)); P /= P.sum(1, keepdims=True)
            rows.append(report(name, P, t))
        show(rows)
