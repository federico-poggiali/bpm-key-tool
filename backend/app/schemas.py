"""Pydantic models for the JSON API (the frontend generates its types from these)."""
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")
Status = Literal["owned", "wantlist", "considering"]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class NoteOut(BaseModel):
    id: int
    type: str
    body: str
    record_id: int | None
    track_id: int | None
    created_at: str
    updated_at: str


class TrackOut(BaseModel):
    id: int
    record_id: int
    position: str
    artist: str | None
    title: str
    duration_sec: int | None
    bpm: float | None
    key: str | None
    camelot_key: str | None
    confidence: float | None
    analysis_raw: dict | None
    audio_path: str | None
    analyzed_at: str | None
    bpm_manual: bool
    key_manual: bool
    tags: list[str] = []
    notes: list[NoteOut] = []


class RecordOut(BaseModel):
    id: int
    discogs_release_id: int | None
    artist: str
    title: str
    label: str | None
    year: int | None
    format: str | None
    cover_url: str | None
    status: Status
    added_at: str
    discogs_collection_synced: bool
    tags: list[str] = []


class RecordSummary(RecordOut):
    track_count: int
    matched_track_ids: list[int] | None = None  # set when a BPM/key filter was used


class RecordDetail(RecordOut):
    tracks: list[TrackOut]
    notes: list[NoteOut]  # record-level notes; track notes are on each track


class IntakeResponse(RecordDetail):
    resolved_from_master: int | None
    jobs: dict[str, int | None] | None


class RecordRef(BaseModel):
    id: int
    artist: str
    title: str
    status: Status
    cover_url: str | None


class TrackHit(TrackOut):
    record: RecordRef


class RecordPatch(BaseModel):
    artist: str | None = Field(default=None, min_length=1)
    title: str | None = Field(default=None, min_length=1)
    label: str | None = None
    year: int | None = Field(default=None, ge=1850, le=2100)
    format: str | None = None
    cover_url: str | None = None
    status: Status | None = None


class TrackPatch(BaseModel):
    """Setting bpm or key locks that field against re-analysis; list it in `unlock` to release it."""
    bpm: float | None = Field(default=None, gt=0, le=400)
    key: str | None = Field(default=None, description="Musical ('F# minor', 'Am') or Camelot ('11A')")
    unlock: list[Literal["bpm", "key"]] = []


class NoteCreate(BaseModel):
    type: str = Field(min_length=1, max_length=50)
    body: str
    record_id: int | None = None
    track_id: int | None = None


class NotePatch(BaseModel):
    type: str | None = Field(default=None, min_length=1, max_length=50)
    body: str | None = None


class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class TagCount(BaseModel):
    name: str
    record_count: int
    track_count: int


class JobOut(BaseModel):
    id: int
    type: str
    status: Literal["queued", "running", "done", "failed"]
    record_id: int | None
    error: str | None
    result: dict | None
    created_at: str
    updated_at: str


class JobStarted(BaseModel):
    job_id: int
    status: str


class SemanticHit(BaseModel):
    score: float
    note: NoteOut
    record: RecordRef
    track: TrackOut | None = None


class AudioMatchedFile(BaseModel):
    track_id: int
    position: str
    file: str
    method: Literal["position", "title"]
    score: float


class UnmatchedFile(BaseModel):
    file: str
    reason: str


class UnmatchedTrack(BaseModel):
    track_id: int
    position: str
    title: str


class AudioMatchReport(BaseModel):
    folder: str | None
    matched: list[AudioMatchedFile]
    unmatched_files: list[UnmatchedFile]
    unmatched_tracks: list[UnmatchedTrack]


class ReembedOut(BaseModel):
    embedded: int


class TagList(BaseModel):
    items: list[TagCount]
