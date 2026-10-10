import { useCallback, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type IntakeResponse, type Status } from "../api/api";
import { AudioMatchPanel } from "../components/AudioMatchPanel";
import { Cover } from "../components/Cover";
import { JobChip } from "../components/JobChip";
import { KeyFormatToggle } from "../components/KeyFormatToggle";
import { TrackTable } from "../components/TrackTable";
import { recordKey, useKeyFormat, useRecord } from "../hooks";
import { STATUSES } from "../lib";
import styles from "./AddRecordPage.module.css";

export default function AddRecordPage() {
  const client = useQueryClient();
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("owned");
  const [keyFormat, setKeyFormat] = useKeyFormat();
  const [result, setResult] = useState<{ data: IntakeResponse; existed: boolean } | null>(null);
  const [analysisJob, setAnalysisJob] = useState<number | null>(null);
  const [syncJob, setSyncJob] = useState<number | null>(null);
  const [analysisDone, setAnalysisDone] = useState(true);

  const intake = useMutation({
    mutationFn: () => api.intake({ discogs_url: url.trim(), status }),
    onSuccess: ({ data, status: http }) => {
      setResult({ data, existed: http === 200 });
      setAnalysisJob(data.jobs?.analysis ?? null);
      setSyncJob(data.jobs?.discogs_sync ?? null);
      setAnalysisDone(data.jobs?.analysis == null);
      client.invalidateQueries({ queryKey: ["records"] });
    },
  });
  const analyze = useMutation({
    mutationFn: (id: number) => api.analyze(id),
    onSuccess: ({ job_id }) => { setAnalysisJob(job_id); setAnalysisDone(false); },
  });
  const sync = useMutation({
    mutationFn: (id: number) => api.syncDiscogs(id),
    onSuccess: ({ job_id }) => setSyncJob(job_id),
  });

  const recordId = result?.data.id ?? 0;
  const record = useRecord(recordId, result != null && !analysisDone);
  const onAnalysisSettled = useCallback(() => {
    setAnalysisDone(true);
    client.invalidateQueries({ queryKey: recordKey(recordId) });
    client.invalidateQueries({ queryKey: ["audio-match", recordId] });
    client.invalidateQueries({ queryKey: ["records"] });
  }, [client, recordId]);
  const onSyncSettled = useCallback(() => client.invalidateQueries({ queryKey: recordKey(recordId) }), [client, recordId]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (url.trim()) intake.mutate();
  };
  const shown = record.data ?? (result ? { ...result.data } : null);
  const isOwned = (shown?.status ?? status) === "owned";

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <span className="micro">add record</span>
        <h1>Paste a record. <span>Get its BPM and key.</span></h1>
        <form onSubmit={submit} className={styles.form}>
          <label className={styles.field}>
            <span className="sr">Discogs link</span>
            <input
              type="url" inputMode="url" required autoFocus autoComplete="off"
              placeholder="discogs.com/release/…" value={url} onChange={(e) => setUrl(e.target.value)}
            />
          </label>
          <button className="primary" type="submit" disabled={intake.isPending}>
            {intake.isPending ? "Adding…" : "Add record"}
          </button>
        </form>
        <fieldset className={styles.status}>
          <legend className="micro">add as</legend>
          {STATUSES.map((s) => (
            <label key={s} className={status === s ? styles.on : ""}>
              <input type="radio" name="status" value={s} checked={status === s} onChange={() => setStatus(s)} />
              {s}
            </label>
          ))}
        </fieldset>
        <p className={styles.hint}>Release or master links both work. Owned records are also added to your Discogs collection.</p>
        {intake.isError && <p className={styles.error} role="alert">{intake.error.message}</p>}
      </header>

      {shown && result && (
        <section className={styles.result} aria-label="Added record">
          {result.existed && (
            <p className={styles.dupe} role="status">
              <b>Already in your library.</b> It was not added twice. <Link to={`/records/${shown.id}`}>Open the record</Link>
            </p>
          )}
          {result.data.resolved_from_master != null && (
            <p className={styles.hint}>Master link: using its main release.</p>
          )}
          <div className={styles.release}>
            <div className={styles.cover}><Cover url={shown.cover_url} alt={`${shown.artist} - ${shown.title}`} /></div>
            <div>
              <h2>{shown.title}</h2>
              <p>{shown.artist}</p>
              <p className={styles.meta}>{[shown.label, shown.year, shown.format].filter(Boolean).join(" · ")}</p>
              {!result.existed && <Link className={styles.open} to={`/records/${shown.id}`}>Open record →</Link>}
            </div>
          </div>

          <div className={styles.jobs}>
            <JobChip label="Analysis" jobId={analysisJob} onSettled={onAnalysisSettled}
              onRetry={() => analyze.mutate(shown.id)} retrying={analyze.isPending} />
            <JobChip label="Discogs sync" jobId={syncJob} canStart={isOwned}
              idleText={isOwned ? "not started" : "only owned records sync"}
              onSettled={onSyncSettled} onRetry={() => sync.mutate(shown.id)} retrying={sync.isPending} />
          </div>

          <AudioMatchPanel recordId={shown.id} onAssigned={() => analyze.mutate(shown.id)} />

          <div className={styles.tracksHead}>
            <span className="micro">tracklist</span>
            <KeyFormatToggle value={keyFormat} onChange={setKeyFormat} />
          </div>
          <TrackTable record={shown} editable={false} keyFormat={keyFormat} />
        </section>
      )}
    </div>
  );
}
