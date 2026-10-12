import logging
import queue
import sqlite3
import threading
from collections.abc import Callable

from app.db import connect, jobs

log = logging.getLogger(__name__)

Handler = Callable[[sqlite3.Connection, dict], dict | None]


class JobRunner:
    """Runs queued jobs one at a time on a worker thread; state lives in the `jobs` table.

    Without start() nothing runs in the background; run_pending() processes the queue inline,
    which is what the tests use.
    """

    def __init__(self, handlers: dict[str, Handler],
                 connect_fn: Callable[[], sqlite3.Connection] = connect,
                 on_done: Callable[[], None] | None = None):
        self.handlers = handlers
        self._on_done = on_done  # called after every job, e.g. to refresh the vault
        self._connect = connect_fn
        self._queue: queue.Queue[int | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    def enqueue(self, type: str, record_id: int | None = None, params: dict | None = None) -> int:
        conn = self._connect()
        try:
            job_id = jobs.create(conn, type, record_id, params)
        finally:
            conn.close()
        if self._thread:
            self._queue.put(job_id)
        return job_id

    def run_job(self, job_id: int) -> None:
        conn = self._connect()
        try:
            job = jobs.get(conn, job_id)
            if job is None or job["status"] != "queued":
                return
            jobs.set_status(conn, job_id, "running")
            try:
                result = self.handlers[job["type"]](conn, job)
            except Exception as exc:
                log.exception("job %s (%s) failed", job_id, job["type"])
                jobs.set_status(conn, job_id, "failed", error=f"{type(exc).__name__}: {exc}")
            else:
                jobs.set_status(conn, job_id, "done", result=result)
        finally:
            conn.close()
            if self._on_done:
                self._on_done()

    def run_pending(self) -> None:
        conn = self._connect()
        try:
            ids = [j["id"] for j in jobs.list_by_status(conn, "queued")]
        finally:
            conn.close()
        for job_id in ids:
            self.run_job(job_id)

    def start(self) -> None:
        conn = self._connect()
        try:
            for job in jobs.list_by_status(conn, "running"):
                jobs.set_status(conn, job["id"], "failed", error="interrupted by a restart")
            for job in jobs.list_by_status(conn, "queued"):
                self._queue.put(job["id"])
        finally:
            conn.close()
        self._thread = threading.Thread(target=self._loop, name="job-runner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread:
            self._queue.put(None)
            self._thread.join(timeout=5)
            self._thread = None

    def _loop(self) -> None:
        while (job_id := self._queue.get()) is not None:
            self.run_job(job_id)
