"""What goes on a record's labels: built from the database, editable before it is rendered.

Every printed value is a plain string so the editor can change it freely. Nothing here writes to
the database: edits apply to the print only."""
import re
from typing import Literal

from pydantic import BaseModel, Field

MainField = Literal["label", "catno", "year", "country", "styles", "note", "qr"]
TrackField = Literal["bpm", "key", "tags", "note"]


class LabelTrack(BaseModel):
    position: str
    bpm: str | None = None
    key: str | None = None
    tags: list[str] = []
    note: str | None = None
    skip: bool = Field(default=False, description="Leave this track off the tracks label")
    hidden: list[TrackField] = []


class LabelData(BaseModel):
    artist: str
    label: str | None = None
    catno: str | None = None
    title: str
    year: str | None = None
    country: str | None = Field(default=None, description="Not stored: type it in if you want it printed")
    styles: list[str] = []
    note: str | None = None
    qr_url: str | None = Field(default=None, description="The Discogs page the QR code opens")
    hidden: list[MainField] = []
    tracks: list[LabelTrack] = []


_DISCOGS_SUFFIX = re.compile(r"\s*\(\d+\)(?=\s*(?:[&,/]|$))")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def clean_artist(name: str) -> str:
    """Discogs tells namesakes apart with a number: 'Jeff Mills (2)'. Not for print."""
    return _DISCOGS_SUFFIX.sub("", name).strip()


def first_sentence(notes: list[dict]) -> str | None:
    """One sentence for the label: the first prose note (any note if none is prose), cut at the
    first full stop."""
    ordered = sorted(notes, key=lambda n: n["type"] != "prose")
    for note in ordered:
        text = " ".join(note["body"].split())
        if text:
            return _SENTENCE_END.split(text, maxsplit=1)[0]
    return None


def _bpm(value: float | None) -> str | None:
    return None if value is None else f"{round(value, 1):g}"


def build(record: dict) -> LabelData:
    """`record` is queries.record_detail(): the record with its tracks, tags and notes."""
    release_id = record["discogs_release_id"]
    return LabelData(
        artist=clean_artist(record["artist"]),
        label=record["label"], catno=record["catno"], title=record["title"],
        year=str(record["year"]) if record["year"] else None,
        styles=record["styles"] or [],
        note=first_sentence(record["notes"]),
        qr_url=f"https://www.discogs.com/release/{release_id}" if release_id else None,
        tracks=[LabelTrack(position=t["position"], bpm=_bpm(t["bpm"]),
                           key=t["camelot_key"] or t["key"], tags=t["tags"],
                           note=first_sentence(t["notes"]))
                for t in record["tracks"]],
    )
