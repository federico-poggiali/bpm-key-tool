"""Build the benchmark set: tracks of the listed Discogs releases, their database-consensus
key (pseudo ground truth, Camelot) and a local audio file for every labelled track.

Resumable: re-running skips tracks already collected.  Output: benchmark/labels.json
"""
from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from bpmkey.analyze import AudioUnavailable, download_audio, download_direct  # noqa: E402
from bpmkey.discogs import DiscogsClient  # noqa: E402
from bpmkey.lookup import PROVIDERS  # noqa: E402
from bpmkey.sources import finders_for  # noqa: E402

LABELS = ROOT / "labels.json"
AUDIO = ROOT / "audio"
MIN_AGREE = 2  # databases that must give the same Camelot code
MAX_ATTEMPTS = 4
log = logging.getLogger("collect")


def consensus(keys: dict) -> str | None:
    if not keys:
        return None
    code, n = Counter(keys.values()).most_common(1)[0]
    return code if n >= MIN_AGREE else None


def weak_label(keys: dict) -> str | None:
    """Fallback when the databases disagree or only one knows the track (lower trust)."""
    return next(iter(keys.values())) if len(keys) == 1 else None


def fetch_audio(track, finders, dest_stem: Path) -> Path | None:
    tried = 0
    for f in finders:
        try:
            sources = f.find(track)
        except Exception as e:
            log.warning("%s search failed: %s", f.name, e)
            continue
        for src in sources:
            if tried >= MAX_ATTEMPTS:
                return None
            tried += 1
            dest_stem.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest_stem.parent / (dest_stem.name + ".dl")
            tmp.mkdir(exist_ok=True)
            try:
                p = (download_direct if src.kind == "itunes" else download_audio)(src.url, tmp)
                final = dest_stem.with_suffix(p.suffix)
                p.rename(final)
                return final, src.kind
            except AudioUnavailable as e:
                log.info("unavailable %s: %s", src.url, e)
            finally:
                for x in tmp.glob("*"):
                    x.unlink()
                tmp.rmdir()
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    urls = [u.strip() for u in (ROOT / "urls.txt").read_text().split() if u.strip()]
    data = json.loads(LABELS.read_text()) if LABELS.exists() else {}
    client = DiscogsClient()
    for url in urls:
        release, tracks, _ = client.tracks(url)
        finders = finders_for(release, client)
        log.info("== %s (%d tracks)", release.get("title"), len(tracks))
        for t in tracks:
            key = f"{t.release_id}:{t.position}"
            rec = data.get(key)
            if rec and "weak_label" not in rec:
                rec["weak_label"] = weak_label(rec["db_keys"])
            if rec and (rec.get("audio") or not (rec["label"] or rec["weak_label"]) or rec.get("audio_failed")):
                continue
            if not rec:
                keys = {}
                for p in PROVIDERS:
                    try:
                        m = p.query(t)
                    except Exception as e:
                        log.warning("%s failed: %s", p.name, e)
                        continue
                    if m and m.camelot:
                        keys[m.origin] = m.camelot
                rec = data[key] = {"release": release.get("title"), "release_id": t.release_id,
                                   "position": t.position, "artist": t.artist, "title": t.title,
                                   "duration": t.duration, "db_keys": keys, "label": consensus(keys), "weak_label": weak_label(keys)}
            if (rec["label"] or rec["weak_label"]) and not rec.get("audio"):
                got = fetch_audio(t, finders, AUDIO / f"{t.release_id}_{t.position.replace('/', '-')}")
                if got:
                    rec["audio"], rec["audio_kind"] = str(got[0].relative_to(ROOT)), got[1]
                else:
                    rec["audio_failed"] = True
            log.info("%-8s %-45s keys=%s label=%s/%s audio=%s", t.position, f"{t.artist} - {t.title}"[:45],
                     rec["db_keys"], rec["label"], rec["weak_label"], rec.get("audio"))
            LABELS.write_text(json.dumps(data, indent=1))
    n_lab = sum(1 for r in data.values() if r["label"])
    n_aud = sum(1 for r in data.values() if r.get("audio"))
    log.info("DONE: %d tracks, %d labelled, %d with audio", len(data), n_lab, n_aud)


if __name__ == "__main__":
    main()
