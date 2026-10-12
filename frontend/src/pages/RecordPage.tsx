import { useCallback, useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/api";
import { AudioMatchPanel } from "../components/AudioMatchPanel";
import { Cover } from "../components/Cover";
import { JobChip } from "../components/JobChip";
import { KeyFormatToggle } from "../components/KeyFormatToggle";
import { QuickNote } from "../components/QuickNote";
import { NotesPanel } from "../components/NotesPanel";
import { SaveIndicator } from "../components/SaveIndicator";
import { ShelfPrompt } from "../components/ShelfPrompt";
import { Skeleton } from "../components/Skeleton";
import { StyleEditor } from "../components/StyleEditor";
import { TagEditor } from "../components/TagEditor";
import { TrackTable } from "../components/TrackTable";
import { recordKey, usePatchRecord, useKeyFormat, useRecord, useStyleMutations, useStyles, useTagMutations, useTags } from "../hooks";
import { LOW_CONFIDENCE } from "../lib";
import styles from "./RecordPage.module.css";

/** Passed in router state by the add-record page, so the record can say what happened.
    askShelf: it was added as owned, so ask where it goes on the shelf. */
export type Arrival = { existed: boolean; fromMaster: boolean; askShelf?: boolean };

export default function RecordPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const { hash, state } = useLocation();
  const arrival = state as Arrival | null;
  const client = useQueryClient();
  const [analysisJob, setAnalysisJob] = useState<number | null>(null);
  const [syncJob, setSyncJob] = useState<number | null>(null);
  const [analysing, setAnalysing] = useState(false);
  const record = useRecord(id, analysing);
  const patch = usePatchRecord(id);
  const tags = useTagMutations(id);
  const allTags = useTags();
  const styleMutations = useStyleMutations(id);
  const allStyles = useStyles();
  const [keyFormat, setKeyFormat] = useKeyFormat();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [askShelf, setAskShelf] = useState(!!arrival?.askShelf);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [analysisIds, setAnalysisIds] = useState<number[] | null>(null); // tracks of the running analysis; null = whole record
  const analyze = useMutation({
    mutationFn: (trackIds?: number[]) => api.analyze(id, trackIds),
    onSuccess: ({ job_id }, trackIds) => { setAnalysisIds(trackIds ?? null); setAnalysisJob(job_id); setAnalysing(true); },
  });
  // Analysis results wait as proposals until validated; `conflict` holds tracks whose hand-set values they'd replace.
  const [conflict, setConflict] = useState<{ ids: number[]; manual: string[] } | null>(null);
  const validate = useMutation({
    mutationFn: ({ ids, overwrite }: { ids: number[]; overwrite: boolean }) => api.validate(id, ids, overwrite),
    onSuccess: (detail) => { setConflict(null); client.setQueryData(recordKey(id), detail); refresh(); },
  });
  const discard = useMutation({
    mutationFn: (ids?: number[]) => api.discard(id, ids),
    onSuccess: (detail) => { setConflict(null); client.setQueryData(recordKey(id), detail); },
  });
  const [syncRunning, setSyncRunning] = useState(false);
  const sync = useMutation({ mutationFn: () => api.syncDiscogs(id), onSuccess: ({ job_id }) => { setSyncJob(job_id); setSyncRunning(true); } });
  const del = useMutation({
    mutationFn: () => api.deleteRecord(id),
    onSuccess: () => { client.invalidateQueries({ queryKey: ["records"] }); navigate("/"); },
  });
  const refresh = useCallback(() => {
    client.invalidateQueries({ queryKey: ["records"] });
    client.invalidateQueries({ queryKey: recordKey(id) });
    client.invalidateQueries({ queryKey: ["audio-match", id] });
  }, [client, id]);

  // Opened from a search result: scroll to the note and highlight it.
  useEffect(() => {
    if (!record.data || !hash.startsWith("#note-")) return;
    const el = document.getElementById(hash.slice(1));
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.setAttribute("data-highlight", "true");
    }
  }, [record.data, hash]);

  if (record.isError) {
    const missing = record.error instanceof ApiError && record.error.status === 404;
    return (
      <div className={styles.missing}>
        <span className="micro">{missing ? "404" : "error"}</span>
        <h1>{missing ? "That record isn't in your library." : "Couldn't load this record."}</h1>
        <Link className="ghost" to="/">Back to the library</Link>
      </div>
    );
  }
  if (!record.data) return <Skeleton rows={6} />;

  const r = record.data;
  const analysisBusy = analyze.isPending || analysing;
  const busyIds = analysing ? new Set(analysisIds ?? r.tracks.map((t) => t.id)) : undefined;
  const recordNote = r.notes.map((n) => n.body.trim()).find(Boolean);
  const pending = r.tracks.filter((t) => t.proposal);
  const lowCount = pending.filter((t) => t.proposal!.confidence != null && t.proposal!.confidence < LOW_CONFIDENCE).length;
  const pickedPending = pending.filter((t) => selected.has(t.id));
  const startValidate = (tracks: typeof pending) => {
    const manual = tracks.filter((t) => {
      const p = t.proposal!;
      return (t.key_manual && p.camelot_key != null && p.camelot_key !== t.camelot_key);
    });
    const ids = tracks.map((t) => t.id);
    if (manual.length) setConflict({ ids, manual: manual.map((t) => t.position || t.title) });
    else validate.mutate({ ids, overwrite: false });
  };

  return (
    <article className={styles.page}>
      {arrival?.existed && <p className={styles.notice} role="status"><b>Already in your library.</b> It was not added twice.</p>}
      {arrival?.fromMaster && <p className={styles.notice}>Master link: using its main release.</p>}
      {askShelf && r.status === "owned" && <ShelfPrompt recordId={r.id} onDone={() => setAskShelf(false)} />}
      <header className={styles.head}>
        <div className={styles.cover}><Cover url={r.cover_url} alt={`${r.artist} - ${r.title}`} /></div>
        <div className={styles.meta}>
          <div className={styles.topline}>
            <span className="micro">record</span>
            <SaveIndicator />
          </div>
          {pending.length > 0 && (
            <span className={styles.pendingBadge}>{pending.length} {pending.length === 1 ? "track" : "tracks"} to validate</span>
          )}
          <h1>{r.title}</h1>
          <p className={styles.artist}>{r.artist}</p>
          <p className={styles.sub}>{[r.label, r.catno, r.year, r.format].filter(Boolean).join(" · ")}</p>
          {recordNote && <p className={styles.noteLine}>{recordNote}</p>}
          {r.status === "owned" ? (
            <p className={styles.owned}>Owned</p>
          ) : (
            <div className={styles.owned}>
              <span>{r.status}</span>
              <button className="primary small" onClick={() => patch.mutate({ status: "owned" }, { onSuccess: () => { client.invalidateQueries({ queryKey: ["crate"] }); setAskShelf(true); } })}>Add to library</button>
              {r.status !== "wantlist" && <button className="ghost small" onClick={() => patch.mutate({ status: "wantlist" })}>Add to wishlist</button>}
            </div>
          )}
          <StyleEditor
            styles={r.styles ?? []} manual={r.styles_manual} suggestions={(allStyles.data ?? []).map((s) => s.name)}
            readOnly={arrival != null}
            onChange={(next) => styleMutations.set.mutate(next)}
            onReset={r.discogs_release_id != null ? () => styleMutations.reset.mutate() : undefined}
          />
          <TagEditor
            label="this record" tags={r.tags ?? []} options={allTags.data ?? []}
            onAdd={(name) => tags.add.mutate({ kind: "record", id, name })}
            onRemove={(name) => tags.remove.mutate({ kind: "record", id, name })}
          />
          <div className={styles.actions}>
            {r.discogs_release_id != null && (
              <a className="ghost" href={`https://www.discogs.com/release/${r.discogs_release_id}`} target="_blank" rel="noreferrer">Discogs ↗</a>
            )}
            <Link className="ghost" to={`/records/${id}/label`}>Make label</Link>
            {confirmDelete ? (
              <>
                <button className="ghost danger" onClick={() => del.mutate()} disabled={del.isPending}>Confirm delete</button>
                <button className="ghost" onClick={() => setConfirmDelete(false)}>Keep</button>
              </>
            ) : (
              <button className="ghost danger" onClick={() => setConfirmDelete(true)}>Delete record</button>
            )}
          </div>
        </div>
        <div className={styles.noteSlot}>
          <QuickNote recordId={r.id} title={r.title} variant="hero" filled={r.notes.some((n) => n.body.trim() !== "")} />
        </div>
      </header>

      <section aria-label="Tracks">
        <div className={styles.sectionHead}>
          <h2>Tracklist</h2>
          <KeyFormatToggle value={keyFormat} onChange={setKeyFormat} />
        </div>
        <div className={styles.toolbar}>
          <div className={styles.toolbarActions}>
            <button className="primary" onClick={() => analyze.mutate([...selected])} disabled={analysisBusy || selected.size === 0 || r.discogs_release_id == null}>
              Analyse selected{selected.size ? ` (${selected.size})` : ""}
            </button>
            <button className="ghost" onClick={() => analyze.mutate(undefined)} disabled={analysisBusy || r.discogs_release_id == null}>Analyse whole record</button>
            {r.status === "owned" && (
              <button className="ghost" onClick={() => sync.mutate()} disabled={sync.isPending || syncRunning}>
                {r.discogs_collection_synced ? "In Discogs collection · sync again" : "Add to Discogs collection"}
              </button>
            )}
          </div>
          {(analysisJob != null || syncJob != null) && (
            <div className={styles.jobs}>
              {analysisJob != null && <JobChip label="Analysis" jobId={analysisJob} onSettled={() => { setAnalysing(false); refresh(); }} onRetry={() => analyze.mutate(analysisIds ?? undefined)} />}
              {syncJob != null && <JobChip label="Discogs sync" jobId={syncJob} onSettled={() => { setSyncRunning(false); refresh(); }} onRetry={() => sync.mutate()} />}
            </div>
          )}
          {pending.length > 0 && (
            <div className={styles.validateBar} role="region" aria-label="Analysis to validate">
              {conflict ? (
                <>
                  <p><b>{conflict.manual.join(", ")}</b> {conflict.manual.length === 1 ? "has" : "have"} a BPM or key you set by hand. Replace {conflict.manual.length === 1 ? "it" : "them"} with the new analysis?</p>
                  <div className={styles.toolbarActions}>
                    <button className="primary small" disabled={validate.isPending} onClick={() => validate.mutate({ ids: conflict.ids, overwrite: true })}>Replace mine</button>
                    <button className="ghost small" disabled={validate.isPending} onClick={() => validate.mutate({ ids: conflict.ids, overwrite: false })}>Keep mine</button>
                    <button className="ghost small" onClick={() => setConflict(null)}>Cancel</button>
                  </div>
                </>
              ) : r.status === "owned" ? (
                <>
                  <p>New analysis is ready for {pending.length} {pending.length === 1 ? "track" : "tracks"}. Nothing is saved until you validate it.{lowCount > 0 && ` ${lowCount} ${lowCount === 1 ? "has" : "have"} a key the analysis was unsure about. Open the arrow next to it to see how sure.`}</p>
                  <div className={styles.toolbarActions}>
                    <button className="primary small" disabled={validate.isPending || pickedPending.length === 0} onClick={() => startValidate(pickedPending)}>
                      Validate selected{pickedPending.length ? ` (${pickedPending.length})` : ""}
                    </button>
                    <button className="ghost small" disabled={validate.isPending} onClick={() => startValidate(pending)}>Validate all</button>
                    <button className="ghost small danger" disabled={discard.isPending} onClick={() => discard.mutate()}>Discard</button>
                  </div>
                </>
              ) : (
                <>
                  <p>New analysis is ready for {pending.length} {pending.length === 1 ? "track" : "tracks"}. Add the record to your library to validate it.</p>
                  <div className={styles.toolbarActions}>
                    <button className="ghost small danger" disabled={discard.isPending} onClick={() => discard.mutate()}>Discard</button>
                  </div>
                </>
              )}
            </div>
          )}
          <p className={styles.hint}>Tick tracks to analyse just those, or analyse the whole record. Or skip analysis and only add it to your collection.</p>
        </div>
        <TrackTable record={r} editable keyFormat={keyFormat} busyIds={busyIds} selection={{ ids: selected, onChange: setSelected }}
          onUse={r.status === "owned" ? (t) => startValidate([t]) : undefined} onPass={(t) => discard.mutate([t.id])} />
        <p className={styles.hint}>Click a BPM or key to set it yourself. A value you set is marked manual; validating new analysis asks before replacing it.</p>
      </section>

      <AudioMatchPanel recordId={id} onAssigned={() => analyze.mutate(undefined)} />
      <NotesPanel record={r} />
    </article>
  );
}
