import { useCallback, useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, type Status } from "../api/api";
import { AudioMatchPanel } from "../components/AudioMatchPanel";
import { Cover } from "../components/Cover";
import { JobChip } from "../components/JobChip";
import { KeyFormatToggle } from "../components/KeyFormatToggle";
import { NotesPanel } from "../components/NotesPanel";
import { SaveIndicator } from "../components/SaveIndicator";
import { Skeleton } from "../components/Skeleton";
import { TagEditor } from "../components/TagEditor";
import { TrackTable } from "../components/TrackTable";
import { recordKey, usePatchRecord, useKeyFormat, useRecord, useTagMutations, useTags } from "../hooks";
import { STATUSES, formatBpm } from "../lib";
import styles from "./RecordPage.module.css";

export default function RecordPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const { hash } = useLocation();
  const client = useQueryClient();
  const record = useRecord(id);
  const patch = usePatchRecord(id);
  const tags = useTagMutations(id);
  const allTags = useTags();
  const [keyFormat, setKeyFormat] = useKeyFormat();
  const [analysisJob, setAnalysisJob] = useState<number | null>(null);
  const [syncJob, setSyncJob] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const analyze = useMutation({ mutationFn: () => api.analyze(id), onSuccess: ({ job_id }) => setAnalysisJob(job_id) });
  const sync = useMutation({ mutationFn: () => api.syncDiscogs(id), onSuccess: ({ job_id }) => setSyncJob(job_id) });
  const del = useMutation({
    mutationFn: () => api.deleteRecord(id),
    onSuccess: () => { client.invalidateQueries({ queryKey: ["records"] }); navigate("/"); },
  });
  const refresh = useCallback(() => {
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
  const bpms = r.tracks.map((t) => t.bpm).filter((b): b is number => b != null);
  const keys = [...new Set(r.tracks.map((t) => t.camelot_key).filter(Boolean))];

  return (
    <article className={styles.page}>
      <header className={styles.head}>
        <div className={styles.cover}><Cover url={r.cover_url} alt={`${r.artist} - ${r.title}`} /></div>
        <div className={styles.meta}>
          <div className={styles.topline}>
            <span className="micro">record</span>
            <SaveIndicator />
          </div>
          <h1>{r.title}</h1>
          <p className={styles.artist}>{r.artist}</p>
          <p className={styles.sub}>{[r.label, r.year, r.format].filter(Boolean).join(" · ")}</p>
          <dl className={styles.facts}>
            <div><dt className="micro">bpm</dt><dd>{bpms.length ? (Math.min(...bpms) === Math.max(...bpms) ? formatBpm(bpms[0]) : `${formatBpm(Math.min(...bpms))}–${formatBpm(Math.max(...bpms))}`) : "·"}</dd></div>
            <div><dt className="micro">keys</dt><dd>{keys.length ? keys.join(" ") : "·"}</dd></div>
            <div>
              <dt className="micro"><label htmlFor="status">status</label></dt>
              <dd>
                <select id="status" className="field-input" value={r.status} onChange={(e) => patch.mutate({ status: e.target.value as Status })}>
                  {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </dd>
            </div>
          </dl>
          <TagEditor
            label="this record" tags={r.tags ?? []} suggestions={(allTags.data ?? []).map((t) => t.name)}
            onAdd={(name) => tags.add.mutate({ kind: "record", id, name })}
            onRemove={(name) => tags.remove.mutate({ kind: "record", id, name })}
          />
          <div className={styles.actions}>
            {r.discogs_release_id != null && (
              <a className="ghost" href={`https://www.discogs.com/release/${r.discogs_release_id}`} target="_blank" rel="noreferrer">Discogs ↗</a>
            )}
            <button className="ghost" onClick={() => analyze.mutate()} disabled={analyze.isPending || r.discogs_release_id == null}>Analyse again</button>
            {r.status === "owned" && (
              <button className="ghost" onClick={() => sync.mutate()} disabled={sync.isPending}>
                {r.discogs_collection_synced ? "In Discogs collection · sync again" : "Add to Discogs collection"}
              </button>
            )}
            {confirmDelete ? (
              <>
                <button className="ghost danger" onClick={() => del.mutate()} disabled={del.isPending}>Confirm delete</button>
                <button className="ghost" onClick={() => setConfirmDelete(false)}>Keep</button>
              </>
            ) : (
              <button className="ghost danger" onClick={() => setConfirmDelete(true)}>Delete record</button>
            )}
          </div>
          {(analysisJob != null || syncJob != null) && (
            <div className={styles.jobs}>
              {analysisJob != null && <JobChip label="Analysis" jobId={analysisJob} onSettled={refresh} onRetry={() => analyze.mutate()} />}
              {syncJob != null && <JobChip label="Discogs sync" jobId={syncJob} onSettled={refresh} onRetry={() => sync.mutate()} />}
            </div>
          )}
        </div>
      </header>

      <section aria-label="Tracks">
        <div className={styles.sectionHead}>
          <h2>Tracklist</h2>
          <KeyFormatToggle value={keyFormat} onChange={setKeyFormat} />
        </div>
        <TrackTable record={r} editable keyFormat={keyFormat} />
        <p className={styles.hint}>Click a BPM or key to set it yourself. A value you set is marked manual and re-analysis leaves it alone.</p>
      </section>

      <AudioMatchPanel recordId={id} onAssigned={() => analyze.mutate()} />
      <NotesPanel record={r} />
    </article>
  );
}
