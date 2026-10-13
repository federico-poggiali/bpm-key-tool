import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/api";
import { JobChip } from "../components/JobChip";
import { useKeysEnabled } from "../hooks";
import { pushToast } from "../toast";
import styles from "./SettingsPage.module.css";

export default function SettingsPage() {
  const client = useQueryClient();
  const status = useQuery({ queryKey: ["vault-status"], queryFn: api.vaultStatus });
  const sync = useMutation({
    mutationFn: api.syncVault,
    onSuccess: () => client.invalidateQueries({ queryKey: ["vault-status"] }),
  });
  const reveal = useMutation({
    mutationFn: api.openVault,
    onSuccess: (r) => pushToast(r.opened ? "Revealed in Finder." : `Not generated yet. It will be at ${r.path}`, "info"),
  });
  const [stylesJob, setStylesJob] = useState<number | null>(null);
  const fetchStyles = useMutation({ mutationFn: api.backfillStyles, onSuccess: ({ job_id }) => setStylesJob(job_id) });
  const [keysOn, setKeysOn] = useKeysEnabled();
  const last = sync.data ?? status.data?.last_sync ?? null;

  return (
    <div className={styles.page}>
      <header>
        <span className="micro">settings</span>
        <h1>Obsidian vault</h1>
      </header>

      <p className={styles.warning} role="note">
        <b>Edits made inside Obsidian are overwritten.</b> The vault is rebuilt from this app on every sync. Change a record, note
        or tag here and it appears in Obsidian; the other way round never happens.
      </p>

      <dl className={styles.facts}>
        <div>
          <dt className="micro">vault folder</dt>
          <dd className="mono" data-testid="vault-dir">{status.data?.vault_dir ?? "…"}</dd>
        </div>
        <div>
          <dt className="micro">last sync</dt>
          <dd data-testid="last-sync">{last ? last.synced_at.replace("T", " ").replace("Z", " UTC") : "not yet"}</dd>
        </div>
        <div>
          <dt className="micro">last result</dt>
          <dd data-testid="last-result">{last ? `${last.written} written · ${last.skipped} unchanged · ${last.deleted} deleted` : "·"}</dd>
        </div>
      </dl>
      {status.data?.last_error && <p className={styles.error} role="alert">The last automatic sync failed: {status.data.last_error}</p>}

      <div className={styles.actions}>
        <button className="primary" onClick={() => sync.mutate()} disabled={sync.isPending}>{sync.isPending ? "Syncing…" : "Sync vault now"}</button>
        <button className="ghost" onClick={() => reveal.mutate()} disabled={reveal.isPending}>Show Dataview examples in Finder</button>
      </div>
      <p className={styles.hint}>The vault also syncs by itself a couple of seconds after any change. The Dataview examples file shows ready-made queries by BPM, key and tag.</p>

      <header>
        <span className="micro">analysis</span>
        <h2>Musical key</h2>
      </header>
      <label className={styles.toggle}>
        <input type="checkbox" checked={keysOn} onChange={(e) => setKeysOn(e.target.checked)} />
        <span>Analyse and show musical key</span>
      </label>
      <p className={styles.hint}>
        BPM is always analysed and shown. With this on, analysis also proposes a key for each track, and the tracklist, library
        filters and track list show keys (Camelot or musical). Off, every key column, filter and picker is hidden.
      </p>

      <header>
        <span className="micro">discogs</span>
        <h2>Styles</h2>
      </header>
      <p className={styles.hint}>
        Records added before styles were imported have none. This asks Discogs once per record (about one a second) and fills in
        the style and catalogue number. Records whose styles you edited are never touched.
      </p>
      <div className={styles.actions}>
        <button className="primary" onClick={() => fetchStyles.mutate()} disabled={fetchStyles.isPending}>Fetch styles for existing records</button>
      </div>
      {stylesJob != null && (
        <JobChip label="Styles" jobId={stylesJob} onRetry={() => fetchStyles.mutate()} retrying={fetchStyles.isPending}
          onSettled={() => { client.invalidateQueries({ queryKey: ["styles"] }); client.invalidateQueries({ queryKey: ["records"] }); }} />
      )}
    </div>
  );
}
