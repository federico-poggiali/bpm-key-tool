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


class ProposalOut(BaseModel):
    """An analysis result waiting to be validated onto its track."""
    bpm: float | None
    key: str | None
    camelot_key: str | None
    confidence: float | None
    analysis_raw: dict | None
    audio_path: str | None
    proposed_at: str


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
    year: int | None = None  # inherited from the record, like styles
    styles: list[str] = []  # inherited from the record
    tags: list[str] = []
    notes: list[NoteOut] = []
    proposal: ProposalOut | None = None  # set on a record's tracks while analysis awaits validation


class RecordOut(BaseModel):
    id: int
    discogs_release_id: int | None
    artist: str
    title: str
    label: str | None
    catno: str | None
    year: int | None
    format: str | None
    cover_url: str | None
    status: Status
    added_at: str
    discogs_collection_synced: bool
    styles: list[str] = []  # Discogs styles; hand-edited when styles_manual is set
    styles_manual: bool
    tags: list[str] = []


class RecordSummary(RecordOut):
    track_count: int
    has_note: bool = False  # a record-level note exists (the one that prints on the label)
    bpm_min: float | None = None
    bpm_max: float | None = None
    camelot_keys: list[str] = []
    matched_track_ids: list[int] | None = None  # set when a BPM/key filter was used


class RecordDetail(RecordOut):
    tracks: list[TrackOut]
    notes: list[NoteOut]  # record-level notes; track notes are on each track


class ValidateRequest(BaseModel):
    track_ids: list[int] = Field(min_length=1)
    overwrite_manual: bool = Field(
        default=False, description="Replace hand-entered BPM/key too (and release their lock)")


class DiscardRequest(BaseModel):
    track_ids: list[int] | None = None  # omitted: every proposal on the record


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
    catno: str | None = None
    year: int | None = Field(default=None, ge=1850, le=2100)
    format: str | None = None
    cover_url: str | None = None
    status: Status | None = None
    styles: list[str] | None = Field(
        default=None, description="Replaces the whole list and locks it against Discogs re-fetches")
    reset_styles: bool = Field(
        default=False, description="Release the lock and re-fetch the styles from Discogs")


class TrackPatch(BaseModel):
    """Setting bpm or key locks that field against re-analysis; list it in `unlock` to release it."""
    bpm: float | None = Field(default=None, gt=0, le=400)
    key: str | None = Field(default=None, description="Musical ('F# minor', 'Am') or Camelot ('11A')")
    unlock: list[Literal["bpm", "key"]] = []


class NoteCreate(BaseModel):
    type: str = Field(default="prose", min_length=1, max_length=50)  # a note is prose; kept for old data
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
    group: str
    record_count: int
    track_count: int


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class GroupRename(GroupIn):
    pass


class TagDefIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class TagDefUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    group_id: int | None = None


class TagDef(BaseModel):
    id: int
    name: str
    record_count: int
    track_count: int


class TagGroup(BaseModel):
    id: int
    name: str
    fixed: bool
    tags: list[TagDef]


class GroupList(BaseModel):
    items: list[TagGroup]


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
    method: Literal["assigned", "position", "title"]
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


class StyleCount(BaseModel):
    name: str
    record_count: int


class StyleList(BaseModel):
    items: list[StyleCount]


class TagList(BaseModel):
    items: list[TagCount]


class AssignAudio(BaseModel):
    file: str = Field(min_length=1)


class ExactNoteHit(BaseModel):
    snippet: str  # matches wrapped in \x02 ... \x03
    note: NoteOut
    record: RecordRef
    track: TrackOut | None = None


class ExactResults(BaseModel):
    notes: list[ExactNoteHit]
    records: list[RecordRef]


class OpenedPath(BaseModel):
    opened: bool
    path: str


# --- Crate: the physical shelf -----------------------------------------------------------------

class CrateRecord(BaseModel):
    id: int
    artist: str
    title: str
    year: int | None
    cover_url: str | None
    styles: list[str] = []
    tags: list[str] = []


class CrateSuggestion(BaseModel):
    section_id: int
    score: int
    reasons: list[str]  # the tags/styles (or artist letter range) that matched


class UnsortedRecord(CrateRecord):
    suggestion: CrateSuggestion | None


class SectionOut(BaseModel):
    id: int
    position: int
    name: str
    records: list[CrateRecord]


class CubeOut(BaseModel):
    id: int
    row: int
    col: int
    name: str
    description: str
    sections: list[SectionOut]


class UnitOut(BaseModel):
    id: int
    name: str
    rows: int
    cols: int
    x: int  # wall position, in cubes from the left
    y: int  # wall position, in cubes from the top
    cubes: list[CubeOut]


class CrateOut(BaseModel):
    units: list[UnitOut]
    unsorted: list[UnsortedRecord]  # owned records not on the shelf yet


class UnitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    rows: int = Field(ge=1, le=8)
    cols: int = Field(ge=1, le=8)
    x: int = Field(default=0, ge=0, le=60)
    y: int = Field(default=0, ge=0, le=30)


class UnitPatch(BaseModel):
    """Shrinking a unit drops the cubes outside it; their records go back to unsorted."""
    name: str | None = Field(default=None, min_length=1, max_length=60)
    rows: int | None = Field(default=None, ge=1, le=8)
    cols: int | None = Field(default=None, ge=1, le=8)
    x: int | None = Field(default=None, ge=0, le=60)
    y: int | None = Field(default=None, ge=0, le=30)


class CubePatch(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=300)


class SectionIn(BaseModel):
    name: str = Field(default="", max_length=60)


class PlaceIn(BaseModel):
    record_ids: list[int] = Field(min_length=1, max_length=500)
    section_id: int | None  # null puts the records back in unsorted
