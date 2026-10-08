"""Local web UI: python -m bpmkey.server  ->  http://127.0.0.1:8765"""
from __future__ import annotations

import argparse
import json
import re
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .discogs import DiscogsClient
from .pipeline import Pipeline

UI = Path(__file__).parent / "ui" / "index.html"
URL_RE = re.compile(r"^https?://(www\.)?discogs\.com/.*?(release|master)/\d+", re.I)


def result_payload(index: int, r) -> dict:
    t = r.track
    return {
        "index": index, "position": t.position, "artist": t.artist, "title": t.title,
        "duration": t.duration, "bpm": r.bpm, "camelot": r.camelot, "status": r.status,
        "note": r.note, "measurements": [asdict(m) for m in t.measurements],
    }


def release_payload(release: dict, tracks) -> dict:
    images = release.get("images") or []
    artists = ", ".join(a["name"] for a in release.get("artists", []))
    return {
        "title": release.get("title"), "artist": artists, "year": release.get("year"),
        "cover": (images[0].get("uri150") or images[0].get("resource_url")) if images else None,
        "tracks": [{"position": t.position, "artist": t.artist, "title": t.title,
                    "duration": t.duration} for t in tracks],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "bpmkey"

    def log_message(self, *a):  # keep the terminal quiet
        pass

    def _allowed(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        cross = self.headers.get("Sec-Fetch-Site") == "cross-site"
        return host in ("127.0.0.1", "localhost") and not cross  # no DNS-rebinding / cross-site use

    def do_GET(self):
        if not self._allowed():
            return self.send_error(403)
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = UI.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == "/api/analyze":
            self._analyze(parse_qs(parsed.query))
        else:
            self.send_error(404)

    def _send(self, event: str, data: dict) -> None:
        self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())
        self.wfile.flush()

    def _analyze(self, q: dict) -> None:
        url = (q.get("url") or [""])[0].strip()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            if not URL_RE.match(url):
                return self._send("fail", {"kind": "url"})
            try:
                client = DiscogsClient()
                release, tracks, _ = client.tracks(url)
            except Exception as e:
                return self._send("fail", {"kind": "discogs", "detail": str(e)[:200]})
            self._send("release", release_payload(release, tracks))
            pipe = Pipeline(analyze=(q.get("analyze", ["1"])[0] != "0"),
                            refresh=(q.get("refresh", ["0"])[0] == "1"))
            counts: dict[str, int] = {}
            self._send("working", {"index": 0})
            for i, r in enumerate(pipe.run_tracks(tracks, release, client)):
                counts[r.status] = counts.get(r.status, 0) + 1
                self._send("track", result_payload(i, r))
                if i + 1 < len(tracks):
                    self._send("working", {"index": i + 1})
            self._send("done", {"counts": counts, "total": len(tracks)})
        except (BrokenPipeError, ConnectionResetError):
            pass  # tab closed: stop quietly
        except Exception as e:
            try:
                self._send("fail", {"kind": "server", "detail": str(e)[:200]})
            except OSError:
                pass


def main() -> None:
    ap = argparse.ArgumentParser(prog="bpmkey.server")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)  # localhost only
    url = f"http://127.0.0.1:{a.port}"
    print(f"Serving on {url}  (Ctrl+C to stop)")
    if not a.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
