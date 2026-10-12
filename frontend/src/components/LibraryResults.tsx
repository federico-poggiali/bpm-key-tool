import { Link } from "react-router-dom";
import type { RecordSummary, TrackHit } from "../api/api";
import { keyLabel, type KeyFormat } from "../lib";
import { Cover } from "./Cover";
import { QuickNote } from "./QuickNote";
import styles from "./LibraryResults.module.css";

export function RecordGrid({ items }: { items: RecordSummary[] }) {
  return (
    <ul className={`${styles.grid} rise`} aria-label="Records">
      {items.map((r) => (
        <li key={r.id} className={styles.item}>
          <span className={styles.noteSlot}><QuickNote recordId={r.id} title={r.title} filled={r.has_note} /></span>
          <Link to={`/records/${r.id}`} className={styles.card}>
            <Cover url={r.cover_url} alt="" />
            <div className={styles.body}>
              <b>{r.title}</b>
              <span>{r.artist}</span>
              <div className={styles.chips}>
                {r.styles.slice(0, 2).map((s) => <i key={s} className={styles.style}>{s}</i>)}
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

export function RecordTable({ items }: { items: RecordSummary[] }) {
  return (
    <table className={styles.table}>
      <caption className="sr">Records</caption>
      <thead>
        <tr><th scope="col"><span className="sr">Cover</span></th><th scope="col">Artist</th><th scope="col">Title</th><th scope="col">Label</th><th scope="col">Year</th><th scope="col">Styles</th><th scope="col">Status</th><th scope="col"><span className="sr">Note</span></th></tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <tr key={r.id}>
            <td className={styles.thumb}><Cover url={r.cover_url} size={36} /></td>
            <td>{r.artist}</td>
            <th scope="row"><Link to={`/records/${r.id}`}>{r.title}</Link></th>
            <td className={styles.dim}>{r.label}</td>
            <td className={styles.dim}>{r.year}</td>
            <td className={styles.dim}>{r.styles.join(", ")}</td>
            <td className={styles.dim}>{r.status}</td>
            <td className={styles.noteCell}><QuickNote recordId={r.id} title={r.title} filled={r.has_note} /></td>
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
        <tr><th scope="col">Pos</th><th scope="col">Artist</th><th scope="col">Title</th><th scope="col">Key</th><th scope="col">Year</th><th scope="col">Styles</th><th scope="col">Record</th></tr>
      </thead>
      <tbody>
        {items.map((t) => (
          <tr key={t.id}>
            <td className={styles.dim}>{t.position}</td>
            <td>{t.artist || t.record.artist}</td>
            <th scope="row"><Link to={`/records/${t.record.id}`}>{t.title}</Link></th>
            <td className={styles.mono}>{keyLabel(t.camelot_key, keyFormat)}</td>
            <td className={styles.dim}>{t.year}</td>
            <td className={styles.dim}>{t.styles.join(", ")}</td>
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
