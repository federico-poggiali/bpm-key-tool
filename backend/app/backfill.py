"""The 'backfill_styles' job: fetch Discogs styles for records saved before styles were imported, and
fill in a missing catalogue number or year while at it. Hand-edited records are never touched, and a
second run does nothing.

CLI: python -m app.backfill   (calls Discogs once per record, within its rate limit)
"""
import logging
import sqlite3
from collections.abc import Callable

from app import config
from app.db import connect, records
from app.discogs import DiscogsClient, DiscogsError, release_to_record

log = logging.getLogger(__name__)

JOB_TYPE = "backfill_styles"


def backfill_styles(conn: sqlite3.Connection, discogs: DiscogsClient) -> dict:
    todo = conn.execute(
        "SELECT id, discogs_release_id, catno, year FROM records WHERE styles IS NULL AND styles_manual = 0 "
        "AND discogs_release_id IS NOT NULL ORDER BY id").fetchall()
    updated, failed = 0, []
    for row in todo:
        try:
            fresh = release_to_record(discogs.release(row["discogs_release_id"]))
        except DiscogsError as exc:
            log.warning("styles backfill skipped record %s: %s", row["id"], exc)
            failed.append({"record_id": row["id"], "error": str(exc)})
            continue
        values = {"styles": fresh["styles"]}
        if row["catno"] is None and fresh["catno"]:
            values["catno"] = fresh["catno"]
        if row["year"] is None and fresh["year"]:
            values["year"] = fresh["year"]
        records.update(conn, row["id"], **values)
        updated += 1
    return {"updated": updated, "failed": failed}


def make_handler(discogs_factory: Callable[[], DiscogsClient]) -> Callable[[sqlite3.Connection, dict], dict]:
    return lambda conn, job: backfill_styles(conn, discogs_factory())


def main() -> None:
    conn = connect()
    result = backfill_styles(conn, DiscogsClient(config.DISCOGS_TOKEN))
    conn.close()
    print(f"styles: {result['updated']} records updated, {len(result['failed'])} failed")


if __name__ == "__main__":
    main()
