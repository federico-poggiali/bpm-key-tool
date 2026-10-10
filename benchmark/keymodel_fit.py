"""Fit/evaluate the committee key model on GiantSteps (cross-validated).

    python benchmark/keymodel_fit.py            # CV report
    python benchmark/keymodel_fit.py --write    # also fit on everything and print the weights
Reads benchmark/profiles.json (python benchmark/profiles.py).
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from bpmkey import keycommittee as kc  # noqa: E402


def load():
    d = json.loads((ROOT / "profiles.json").read_text())
    return np.array(d["truth"]), d["res"]


def fit(X, y, lam, w=None):
    n, K, F = X.shape
    w = np.ones(n) if w is None else w

    def f(theta):
        z = X @ theta
        z -= z.max(1, keepdims=True)
        lse = np.log(np.exp(z).sum(1))
        p = np.exp(z - lse[:, None])
        ll = (z[np.arange(n), y] - lse) * w
        grad = -(X[np.arange(n), y] - np.einsum("nk,nkf->nf", p, X)) * w[:, None]
        return -ll.sum() + lam * theta @ theta, grad.sum(0) + 2 * lam * theta

    return minimize(f, np.zeros(F), jac=True, method="L-BFGS-B").x


def probs(X, theta):
    z = X @ theta
    z -= z.max(1, keepdims=True)
    p = np.exp(z)
    return p / p.sum(1, keepdims=True)


def mirex(pred, t):
    s = np.zeros(len(t))
    for i, (a, b) in enumerate(zip(pred, t)):
        if a == b: s[i] = 1
        else:
            ta, tb, ma, mb = a % 12, b % 12, a >= 12, b >= 12
            if ma == mb and (ta - tb) % 12 in (5, 7): s[i] = .5
            elif ma != mb and ((not mb and ta == (tb + 9) % 12) or (mb and ta == (tb + 3) % 12)): s[i] = .3
            elif ma != mb and ta == tb: s[i] = .2
    return s.mean()


def report(name, p, t, prior_shift=0.0):
    """p: n x 24 probabilities. prior_shift: extra log-odds on major keys (simulates a major-heavier library)."""
    if prior_shift:
        q = p.copy(); q[:, :12] *= np.exp(prior_shift); q /= q.sum(1, keepdims=True)
    else:
        q = p
    pred = q.argmax(1)
    tm, tn = t < 12, t >= 12
    rm, rn = (pred[tm] == t[tm]).mean(), (pred[tn] == t[tn]).mean()
    ll = -np.log(np.clip(q[np.arange(len(t)), t], 1e-6, 1)).mean()
    conf = q.max(1); ok = pred == t
    bins = np.minimum((conf * 5).astype(int), 4)
    ece = sum(abs(ok[bins == b].mean() - conf[bins == b].mean()) * (bins == b).mean() for b in range(5) if (bins == b).any())
    return dict(name=name, exact=(pred == t).mean(), mirex=mirex(pred, t), rec_major=rm, rec_minor=rn,
                bal=(rm + rn) / 2, majorpred=(pred < 12).mean(), logloss=ll, ece=ece)


def show(rows):
    print(f"{'model':44}{'exact':>7}{'MIREX':>7}{'maj-rec':>8}{'min-rec':>8}{'bal-acc':>8}{'%maj-pred':>10}{'logloss':>8}{'ECE':>6}")
    for r in rows:
        print(f"{r['name']:44}{r['exact']:7.3f}{r['mirex']:7.3f}{r['rec_major']:8.3f}{r['rec_minor']:8.3f}"
              f"{r['bal']:8.3f}{r['majorpred']:10.2f}{r['logloss']:8.3f}{r['ece']:6.3f}")


def cv_probs(X, t, lam, folds=10, seeds=(0, 1, 2)):
    out = np.zeros((len(seeds), len(t), 24))
    for si, seed in enumerate(seeds):
        rng = np.random.default_rng(seed)
        fid = np.zeros(len(t), int)
        for grp in (t < 12, t >= 12):  # stratify by mode
            idx = np.where(grp)[0]; rng.shuffle(idx); fid[idx] = np.arange(len(idx)) % folds
        for k in range(folds):
            tr, te = fid != k, fid == k
            out[si, te] = probs(X[te], fit(X[tr], t[tr], lam))
    return out


if __name__ == "__main__":
    t, res = load()
    C = np.load(ROOT / "chroma.npy")
    votes = [{p: tuple(r[p]) for p in kc.ALL_PROFILES} for r in res]
    base = np.array([kc.legacy_probs(v) for v in votes])
    rows = [report("current (edmm + flat spread, bgate in doubt)", base, t)]
    sets = {"edmm+bgate": ("edmm", "bgate"), "5 profiles": ("edmm", "bgate", "edma", "braw", "shaath"),
            "7 profiles": kc.ALL_PROFILES, "edmm only": ("edmm",), "no profiles": ()}
    for name, profs in sets.items():
        for use_c in (False, True):
            if not profs and not use_c: continue
            X = np.array([kc.features(v, profs, C[i] if use_c else None) for i, v in enumerate(votes)])
            for lam in (2.0, 8.0):
                P = cv_probs(X, t, lam, seeds=(0,))
                rows.append(report(f"CV {name}{' +chroma' if use_c else ''} lam={lam}", P[0], t))
    show(rows)
    if "--write" in sys.argv:
        X = np.array([kc.features(v, kc.SHIPPED_PROFILES, C[i]) for i, v in enumerate(votes)])
        theta = fit(X, t, kc.SHIPPED_LAMBDA)
        out = {"profiles": list(kc.SHIPPED_PROFILES), "lambda": kc.SHIPPED_LAMBDA, "n_tracks": len(t),
               "train_major_share": float((t < 12).mean()), "theta": [round(float(x), 4) for x in theta]}
        (ROOT.parent / "bpmkey" / "data").mkdir(exist_ok=True)
        (ROOT.parent / "bpmkey" / "data" / "key_committee.json").write_text(json.dumps(out, indent=1))
        print("wrote bpmkey/data/key_committee.json,", len(theta), "weights")
