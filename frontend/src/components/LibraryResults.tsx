import { Link } from "react-router-dom";
import type { RecordSummary, TrackHit } from "../api/api";
import { formatBpm, keyLabel, type KeyFormat } from "../lib";
import { Cover } from "./Cover";
import { QuickNote } from "./QuickNote";
import styles from "./LibraryResults.module.css";

/** The first two styles as quiet chips, the rest as a count, so rows stay one line tall. */
function Chips({ items }: { items: string[] }) {
  if (items.length === 0) return <span className={styles.none}>—</span>;
  return (
    <span className={styles.chips}>
      {items.slice(0, 2).map((s) => <i key={s} className={styles.style}>{s}</i>)}
      {items.length > 2 && <span className={styles.more}>+{items.length - 2}</span>}
    </span>
  );
}

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
              <Chips items={r.styles} />
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
    <div className={styles.frame}><table className={styles.table}>
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
            <td><Chips items={r.styles} /></td>
            <td><span className={styles.badge} data-status={r.status}>{r.status}</span></td>
            <td className={styles.noteCell}><QuickNote recordId={r.id} title={r.title} filled={r.has_note} /></td>
          </tr>
        ))}
      </tbody>
    </table></div>
  );
}

export function TrackResults({ items, keyFormat, showKeys }: { items: TrackHit[]; keyFormat: KeyFormat; showKeys: boolean }) {
  return (
    <div className={styles.frame}><table className={styles.table}>
      <caption className="sr">Tracks</caption>
      <thead>
        <tr><th scope="col">Pos</th><th scope="col">Artist</th><th scope="col">Title</th><th scope="col">BPM</th>{showKeys && <th scope="col">Key</th>}<th scope="col">Year</th><th scope="col">Styles</th><th scope="col">Record</th></tr>
      </thead>
      <tbody>
        {items.map((t) => (
          <tr key={t.id}>
            <td className={styles.dim}>{t.position}</td>
            <td>{t.artist || t.record.artist}</td>
            <th scope="row"><Link to={`/records/${t.record.id}`}>{t.title}</Link></th>
            <td>{t.bpm != null ? formatBpm(t.bpm) : <span className={styles.none}>—</span>}</td>
            {showKeys && <td>{t.camelot_key ? <span className={styles.key}>{keyLabel(t.camelot_key, keyFormat)}</span> : <span className={styles.none}>—</span>}</td>}
            <td className={styles.dim}>{t.year}</td>
            <td><Chips items={t.styles} /></td>
            <td>
              <Link to={`/records/${t.record.id}`} className={styles.rec}>
                <Cover url={t.record.cover_url} size={28} />{t.record.title}
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table></div>
  );
}
