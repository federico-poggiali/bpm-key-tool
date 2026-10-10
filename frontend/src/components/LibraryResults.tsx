import { Link } from "react-router-dom";
import type { RecordSummary, TrackHit } from "../api/api";
import { formatBpm, keyLabel, type KeyFormat } from "../lib";
import { Cover } from "./Cover";
import styles from "./LibraryResults.module.css";

const bpmText = (r: Pick<RecordSummary, "bpm_min" | "bpm_max">) =>
  r.bpm_min == null ? "" : r.bpm_min === r.bpm_max ? formatBpm(r.bpm_min) : `${formatBpm(r.bpm_min)}–${formatBpm(r.bpm_max)}`;

export function RecordGrid({ items, keyFormat }: { items: RecordSummary[]; keyFormat: KeyFormat }) {
  return (
    <ul className={styles.grid} aria-label="Records">
      {items.map((r) => (
        <li key={r.id}>
          <Link to={`/records/${r.id}`} className={styles.card}>
            <Cover url={r.cover_url} alt="" />
            <div className={styles.body}>
              <b>{r.title}</b>
              <span>{r.artist}</span>
              <div className={styles.chips}>
                {bpmText(r) && <i className={styles.bpm}>{bpmText(r)}<small>bpm</small></i>}
                {r.camelot_keys.slice(0, 3).map((k) => <i key={k} className={styles.key}>{keyLabel(k, keyFormat)}</i>)}
                {r.camelot_keys.length > 3 && <i className={styles.more}>+{r.camelot_keys.length - 3}</i>}
              </div>
              <span className="micro">
                {r.status !== "owned" ? `${r.status} · ` : ""}{r.track_count} track{r.track_count === 1 ? "" : "s"}
                {r.matched_track_ids ? ` · ${r.matched_track_ids.length} match` : ""}
              </span>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function RecordTable({ items, keyFormat }: { items: RecordSummary[]; keyFormat: KeyFormat }) {
  return (
    <table className={styles.table}>
      <caption className="sr">Records</caption>
      <thead>
        <tr><th scope="col"><span className="sr">Cover</span></th><th scope="col">Artist</th><th scope="col">Title</th><th scope="col">Label</th><th scope="col">Year</th><th scope="col" className={styles.num}>BPM</th><th scope="col">Keys</th><th scope="col">Status</th></tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <tr key={r.id}>
            <td className={styles.thumb}><Cover url={r.cover_url} size={36} /></td>
            <td>{r.artist}</td>
            <th scope="row"><Link to={`/records/${r.id}`}>{r.title}</Link></th>
            <td className={styles.dim}>{r.label}</td>
            <td className={styles.dim}>{r.year}</td>
            <td className={styles.num}>{bpmText(r)}</td>
            <td className={styles.mono}>{r.camelot_keys.map((k) => keyLabel(k, keyFormat)).join(" ")}</td>
            <td className={styles.dim}>{r.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function TrackResults({ items, keyFormat }: { items: TrackHit[]; keyFormat: KeyFormat }) {
  return (
    <table className={styles.table}>
      <caption className="sr">Tracks</caption>
      <thead>
        <tr><th scope="col">Pos</th><th scope="col">Artist</th><th scope="col">Title</th><th scope="col" className={styles.num}>BPM</th><th scope="col">Key</th><th scope="col">Record</th></tr>
      </thead>
      <tbody>
        {items.map((t) => (
          <tr key={t.id}>
            <td className={styles.dim}>{t.position}</td>
            <td>{t.artist || t.record.artist}</td>
            <th scope="row"><Link to={`/records/${t.record.id}`}>{t.title}</Link></th>
            <td className={styles.num}>{formatBpm(t.bpm)}</td>
            <td className={styles.mono}>{keyLabel(t.camelot_key, keyFormat)}</td>
            <td>
              <Link to={`/records/${t.record.id}`} className={styles.rec}>
                <Cover url={t.record.cover_url} size={28} />{t.record.title}
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
