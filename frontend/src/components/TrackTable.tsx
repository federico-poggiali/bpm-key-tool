import { Fragment, useState } from "react";
import { altBpm, formatBpm, formatDuration, keyLabel, LOW_CONFIDENCE, WHEEL_KEYS, type KeyFormat } from "../lib";
import type { RecordDetail, TrackOut } from "../api/api";
import { usePatchTrack, useTagMutations, useTags } from "../hooks";
import { TagEditor } from "./TagEditor";
import styles from "./TrackTable.module.css";

type Props = { record: RecordDetail; editable: boolean; keyFormat: KeyFormat; busyIds?: Set<number> };

const SORTED_KEYS = [...WHEEL_KEYS].sort((a, b) => parseInt(a.camelot) - parseInt(b.camelot) || a.camelot.localeCompare(b.camelot));

export function TrackTable({ record, editable, keyFormat, busyIds }: Props) {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <table className={styles.table}>
      <caption className="sr">Tracklist</caption>
      <thead>
        <tr>
          <th scope="col">Pos</th>
          <th scope="col">Title</th>
          <th scope="col" className={styles.num}>BPM</th>
          <th scope="col">Key</th>
          <th scope="col">Confidence</th>
        </tr>
      </thead>
      <tbody>
        {record.tracks.map((track) => (
          <TrackRow
            key={track.id}
            track={track}
            record={record}
            editable={editable}
            keyFormat={keyFormat}
            open={open === track.id}
            working={busyIds?.has(track.id) ?? false}
            onToggle={() => setOpen(open === track.id ? null : track.id)}
          />
        ))}
      </tbody>
    </table>
  );
}

type RowProps = {
  track: TrackOut;
  record: RecordDetail;
  editable: boolean;
  keyFormat: KeyFormat;
  open: boolean;
  working: boolean;
  onToggle: () => void;
};

function TrackRow({ track, record, editable, keyFormat, open, working, onToggle }: RowProps) {
  const patch = usePatchTrack(record.id);
  const tagMutations = useTagMutations(record.id);
  const allTags = useTags();
  const alt = altBpm(track.analysis_raw);
  const lowConfidence = track.confidence != null && !track.key_manual && track.confidence < LOW_CONFIDENCE;
  const raw = (track.analysis_raw ?? {}) as { status?: string; note?: string; measurements?: { origin: string; bpm?: number; camelot?: string }[] };
  const hasData = track.bpm != null || track.camelot_key != null;

  return (
    <Fragment>
      <tr className={`${styles.row} ${open ? styles.open : ""} ${!hasData ? styles.none : ""} ${working ? styles.working : ""}`}>
        <td className={styles.pos}>{track.position || "·"}</td>
        <th scope="row" className={styles.name}>
          <button type="button" className={styles.titleBtn} aria-expanded={open} onClick={onToggle}>
            <b>{track.title}</b>
            {track.artist && track.artist !== record.artist && <span>{track.artist}</span>}
          </button>
        </th>
        <td className={styles.num}>
          <BpmCell track={track} alt={alt} editable={editable} onSave={(bpm) => patch.mutate({ trackId: track.id, patch: { bpm } })}
            onUnlock={() => patch.mutate({ trackId: track.id, patch: { unlock: ["bpm"] } })} />
        </td>
        <td>
          <KeyCell track={track} keyFormat={keyFormat} editable={editable}
            onSave={(key) => patch.mutate({ trackId: track.id, patch: { key } })}
            onUnlock={() => patch.mutate({ trackId: track.id, patch: { unlock: ["key"] } })} />
        </td>
        <td className={styles.conf}>
          {track.confidence != null && !track.key_manual && (
            <span title={lowConfidence ? "The audio analysis was unsure about this key. Check it by ear." : "Audio key confidence"}>
              {lowConfidence && <b className={styles.low}>low </b>}
              {Math.round(track.confidence * 100)}%
            </span>
          )}
        </td>
      </tr>
      {open && (
        <tr className={styles.detailRow}>
          <td />
          <td colSpan={4}>
            <dl className={styles.detail}>
              {track.duration_sec != null && (<><dt>Length</dt><dd>{formatDuration(track.duration_sec)}</dd></>)}
              {raw.status && (<><dt>Result</dt><dd>{raw.status}{raw.note ? `: ${raw.note}` : ""}</dd></>)}
              {raw.measurements?.map((m, i) => (
                <Fragment key={i}>
                  <dt>{m.origin}</dt>
                  <dd>{[m.bpm ? `${formatBpm(m.bpm)} BPM` : "", m.camelot ?? ""].filter(Boolean).join(" · ") || "no value"}</dd>
                </Fragment>
              ))}
              {track.audio_path && (<><dt>Audio file</dt><dd>{track.audio_path.split("/").pop()}</dd></>)}
              {track.analyzed_at && (<><dt>Analysed</dt><dd>{track.analyzed_at.replace("T", " ").replace("Z", "")}</dd></>)}
              {editable && (
                <>
                  <dt>Tags</dt>
                  <dd>
                    <TagEditor
                      label={`track ${track.position || track.title}`}
                      tags={track.tags ?? []}
                      suggestions={(allTags.data ?? []).map((t) => t.name)}
                      onAdd={(name) => tagMutations.add.mutate({ kind: "track", id: track.id, name })}
                      onRemove={(name) => tagMutations.remove.mutate({ kind: "track", id: track.id, name })}
                    />
                  </dd>
                </>
              )}
            </dl>
          </td>
        </tr>
      )}
    </Fragment>
  );
}

function BpmCell({ track, alt, editable, onSave, onUnlock }: {
  track: TrackOut; alt: number | null; editable: boolean; onSave: (bpm: number) => void; onUnlock: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const commit = () => {
    setEditing(false);
    const value = parseFloat(draft.replace(",", "."));
    if (Number.isFinite(value) && value > 0 && value <= 400 && value !== track.bpm) onSave(value);
  };

  if (editing) {
    return (
      <input
        className={`field-input ${styles.bpmInput}`}
        type="number" step="0.1" min="1" max="400" autoFocus
        aria-label={`BPM for ${track.title}`}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") setEditing(false);
        }}
      />
    );
  }
  const value = track.bpm != null ? formatBpm(track.bpm) : "";
  return (
    <span className={styles.bpmWrap}>
      {editable ? (
        <button type="button" className={styles.bpm} aria-label={`Edit BPM for ${track.title}`}
          onClick={() => { setDraft(value); setEditing(true); }}>
          {value || <span className={styles.dash}>set</span>}
        </button>
      ) : (
        <span className={styles.bpm}>{value || <span className={styles.dash}>·</span>}</span>
      )}
      {track.bpm_manual && (
        <span className={styles.manual}>manual{editable && (
          <button type="button" aria-label={`Hand BPM for ${track.title} back to analysis`} title="Hand back to analysis" onClick={onUnlock}>×</button>
        )}</span>
      )}
      {editable && alt != null && alt !== track.bpm && (
        <button type="button" className={styles.alt} title="Use the half/double-tempo reading" aria-label={`Use ${formatBpm(alt)} BPM instead`} onClick={() => onSave(alt)}>
          alt {formatBpm(alt)}
        </button>
      )}
    </span>
  );
}

function KeyCell({ track, keyFormat, editable, onSave, onUnlock }: {
  track: TrackOut; keyFormat: KeyFormat; editable: boolean; onSave: (key: string) => void; onUnlock: () => void;
}) {
  const label = keyLabel(track.camelot_key, keyFormat);
  return (
    <span className={styles.keyWrap}>
      {editable ? (
        <span className={styles.keyPick}>
          <span className={`${styles.key} ${!label ? styles.empty : ""}`} aria-hidden="true">{label || "set"}</span>
          <select
            className={styles.keySelect}
            aria-label={`Key for ${track.title}`}
            value={track.camelot_key ?? ""}
            onChange={(e) => e.target.value && onSave(e.target.value)}
          >
            <option value="">{label ? `${label} (current)` : "Not set"}</option>
            {SORTED_KEYS.map((k) => (
              <option key={k.camelot} value={k.camelot}>{k.camelot} · {k.name}</option>
            ))}
          </select>
        </span>
      ) : (
        <span className={`${styles.key} ${!label ? styles.empty : ""}`}>{label || "·"}</span>
      )}
      {track.key_manual && (
        <span className={styles.manual}>manual{editable && (
          <button type="button" aria-label={`Hand key for ${track.title} back to analysis`} title="Hand back to analysis" onClick={onUnlock}>×</button>
        )}</span>
      )}
    </span>
  );
}
