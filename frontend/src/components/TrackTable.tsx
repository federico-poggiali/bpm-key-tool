import { Fragment, useEffect, useRef, useState } from "react";
import { altBpm, formatBpm, formatDuration, keyLabel, LOW_CONFIDENCE, WHEEL_KEYS, type KeyFormat } from "../lib";
import type { RecordDetail, TrackOut } from "../api/api";
import { usePatchTrack, useTagMutations, useTags } from "../hooks";
import { QuickNote } from "./QuickNote";
import { TagEditor } from "./TagEditor";
import styles from "./TrackTable.module.css";

type Selection = { ids: Set<number>; onChange: (ids: Set<number>) => void };
type Props = {
  record: RecordDetail; editable: boolean; keyFormat: KeyFormat; showKeys: boolean; busyIds?: Set<number>; selection?: Selection;
  /** Decide on a track's waiting analysis from its pop-up: take it, or pass on it. */
  onUse?: (track: TrackOut) => void;
  onPass?: (track: TrackOut) => void;
};

const SORTED_KEYS = [...WHEEL_KEYS].sort((a, b) => parseInt(a.camelot) - parseInt(b.camelot) || a.camelot.localeCompare(b.camelot));

export function TrackTable({ record, editable, keyFormat, showKeys, busyIds, selection, onUse, onPass }: Props) {
  const [open, setOpen] = useState<number | null>(null);
  const all = record.tracks.length > 0 && record.tracks.every((t) => selection?.ids.has(t.id));
  const colSpan = (selection ? 6 : 5) + (showKeys ? 1 : 0);
  return (
    <table className={styles.table}>
      <caption className="sr">Tracklist</caption>
      <thead>
        <tr>
          {selection && (
            <th scope="col" className={styles.pick}>
              <input type="checkbox" aria-label="Select all tracks" checked={all}
                onChange={() => selection.onChange(all ? new Set() : new Set(record.tracks.map((t) => t.id)))} />
            </th>
          )}
          <th scope="col">Pos</th>
          <th scope="col">Title</th>
          <th scope="col" className={styles.num}>Length</th>
          <th scope="col" className={styles.num}>BPM</th>
          {showKeys && <th scope="col">Key</th>}
          <th scope="col">Tags</th>
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
            showKeys={showKeys}
            open={open === track.id}
            working={busyIds?.has(track.id) ?? false}
            colSpan={colSpan}
            onUse={onUse}
            onPass={onPass}
            picked={selection ? selection.ids.has(track.id) : undefined}
            onPick={selection ? () => {
              const next = new Set(selection.ids);
              if (!next.delete(track.id)) next.add(track.id);
              selection.onChange(next);
            } : undefined}
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
  showKeys: boolean;
  open: boolean;
  working: boolean;
  colSpan: number;
  onUse?: (track: TrackOut) => void;
  onPass?: (track: TrackOut) => void;
  picked?: boolean;
  onPick?: () => void;
  onToggle: () => void;
};

function TrackRow({ track, record, editable, keyFormat, showKeys, open, working, colSpan, onUse, onPass, picked, onPick, onToggle }: RowProps) {
  const patch = usePatchTrack(record.id);
  const trackNote = track.notes.map((n) => n.body.trim()).filter(Boolean).join(" · ");
  const raw = (track.analysis_raw ?? {}) as { status?: string; note?: string; measurements?: { origin: string; bpm?: number; camelot?: string }[] };
  const hasData = track.bpm != null || (showKeys && track.camelot_key != null) || track.proposal != null;

  return (
    <Fragment>
      <tr className={`${styles.row} ${open ? styles.open : ""} ${!hasData ? styles.none : ""} ${working ? styles.working : ""}`}>
        {picked !== undefined && (
          <td className={styles.pick}>
            <input type="checkbox" aria-label={`Select ${track.title}`} checked={picked} onChange={onPick} />
          </td>
        )}
        <td className={styles.pos}>{track.position || "·"}</td>
        <th scope="row" className={styles.name}>
          <div className={styles.nameWrap}>
            <button type="button" className={styles.titleBtn} aria-expanded={open} onClick={onToggle}>
              <b>{track.title}</b>
              {track.artist && track.artist !== record.artist && <span>{track.artist}</span>}
              {trackNote && <em className={styles.noteLine}>{trackNote}</em>}
            </button>
            <QuickNote recordId={record.id} title={track.title} track={track} filled={track.notes.some((n) => n.body.trim() !== "")} />
          </div>
        </th>
        <td className={`${styles.num} ${styles.length}`}>{track.duration_sec != null ? formatDuration(track.duration_sec) : ""}</td>
        <td className={styles.num}>
          <BpmCell track={track} alt={altBpm(track.analysis_raw)} editable={editable} keyFormat={keyFormat} showKeys={showKeys}
            onUse={onUse} onPass={onPass}
            onSave={(bpm) => patch.mutate({ trackId: track.id, patch: { bpm } })}
            onUnlock={() => patch.mutate({ trackId: track.id, patch: { unlock: ["bpm"] } })} />
        </td>
        {showKeys && (
          <td>
            <KeyCell track={track} keyFormat={keyFormat} editable={editable}
              onSave={(key) => patch.mutate({ trackId: track.id, patch: { key } })}
              onUnlock={() => patch.mutate({ trackId: track.id, patch: { unlock: ["key"] } })} />
          </td>
        )}
        <td className={styles.tagCell}>
          <div className={styles.tagWrap}>
            {(track.tags ?? []).map((t) => <i key={t} className={styles.tagChip}>{t}</i>)}
            {editable && <TrackTagButton track={track} label={`track ${track.position || track.title}`} />}
          </div>
        </td>
      </tr>
      {open && (
        <tr className={styles.detailRow}>
          <td colSpan={colSpan}>
            <dl className={styles.detail}>
              {raw.status && (<><dt>Result</dt><dd>{raw.status}{raw.note ? `: ${raw.note}` : ""}</dd></>)}
              {raw.measurements?.map((m, i) => (
                <Fragment key={i}>
                  <dt>{m.origin}</dt>
                  <dd>{[m.bpm ? `${formatBpm(m.bpm)} BPM` : "", showKeys ? m.camelot ?? "" : ""].filter(Boolean).join(" · ") || "no value"}</dd>
                </Fragment>
              ))}
              {showKeys && track.confidence != null && !track.key_manual && (<><dt>Key confidence</dt><dd>{Math.round(track.confidence * 100)}%{track.confidence < LOW_CONFIDENCE ? ", low: check it by ear" : ""}</dd></>)}
              {track.audio_path && (<><dt>Audio file</dt><dd>{track.audio_path.split("/").pop()}</dd></>)}
              {track.analyzed_at && (<><dt>Analysed</dt><dd>{track.analyzed_at.replace("T", " ").replace("Z", "")}</dd></>)}
            </dl>
          </td>
        </tr>
      )}
    </Fragment>
  );
}

/** A tag doodle on every track: opens a small pad to add or remove its tags. */
function TrackTagButton({ track, label }: { track: TrackOut; label: string }) {
  const [open, setOpen] = useState(false);
  const mutations = useTagMutations(track.record_id);
  const allTags = useTags();
  const root = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);
  const has = (track.tags ?? []).length > 0;
  return (
    <span className={styles.tagPop} ref={root} onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); }}>
      <button type="button" className={styles.tagAdd} aria-expanded={open}
        aria-label={`${has ? "Edit tags" : "Add a tag"} for ${track.title}`} title={has ? "Edit tags" : "Add a tag"} onClick={() => setOpen(!open)}>
        {has ? "edit" : "+ tag"}
      </button>
      {open && (
        <div className={styles.pop} role="dialog" aria-label={`Tags for ${track.title}`}>
          <TagEditor label={label} tags={track.tags ?? []} options={allTags.data ?? []}
            onAdd={(name) => mutations.add.mutate({ kind: "track", id: track.id, name })}
            onRemove={(name) => mutations.remove.mutate({ kind: "track", id: track.id, name })} />
        </div>
      )}
    </span>
  );
}

/** A waiting analysis value. Clicking it opens a small pop-up with the analysed BPM (and key, when keys
 *  are on), how sure the analysis was, and the choice to use it or pass on it. */
function ProposalPop({ track, keyFormat, showKeys, label, onUse, onPass }: {
  track: TrackOut; keyFormat: KeyFormat; showKeys: boolean; label: string; onUse?: (t: TrackOut) => void; onPass?: (t: TrackOut) => void;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);
  const p = track.proposal!;
  const low = showKeys && p.confidence != null && p.confidence < LOW_CONFIDENCE;
  return (
    <span className={styles.tagPop} ref={root} onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); }}>
      <button type="button" className={styles.proposed} aria-expanded={open} aria-label={`Review the analysis for ${track.title}`}
        title="New analysis, waiting for you" onClick={() => setOpen(!open)}>→ {label}{low ? " · low" : ""}</button>
      {open && (
        <div className={styles.pop} role="dialog" aria-label={`Analysis for ${track.title}`}>
          <dl className={styles.popFacts}>
            {p.bpm != null && (<><dt>BPM</dt><dd>{formatBpm(p.bpm)}</dd></>)}
            {showKeys && p.camelot_key != null && (<><dt>Key</dt><dd>{keyLabel(p.camelot_key, keyFormat)}</dd></>)}
            {showKeys && p.confidence != null && (<><dt>Confidence</dt><dd>{Math.round(p.confidence * 100)}%</dd></>)}
          </dl>
          {low && <p className={styles.popWarn}>The analysis was unsure about this key. Check it by ear.</p>}
          <div className={styles.popActions}>
            {onUse && <button type="button" className="primary small" onClick={() => { setOpen(false); onUse(track); }}>Use</button>}
            {onPass && <button type="button" className="ghost small" onClick={() => { setOpen(false); onPass(track); }}>Pass</button>}
          </div>
        </div>
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

function BpmCell({ track, alt, editable, keyFormat, showKeys, onSave, onUnlock, onUse, onPass }: {
  track: TrackOut; alt: number | null; editable: boolean; keyFormat: KeyFormat; showKeys: boolean;
  onSave: (bpm: number) => void; onUnlock: () => void; onUse?: (t: TrackOut) => void; onPass?: (t: TrackOut) => void;
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
  const p = track.proposal;
  const newBpm = p?.bpm != null && p.bpm !== track.bpm;
  const newKey = showKeys && p?.camelot_key != null && p.camelot_key !== track.camelot_key;
  const proposalLabel = [newBpm ? formatBpm(p!.bpm) : "", newKey ? keyLabel(p!.camelot_key, keyFormat) : ""].filter(Boolean).join(" · ");
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
      {proposalLabel && (
        <ProposalPop track={track} keyFormat={keyFormat} showKeys={showKeys} label={proposalLabel} onUse={onUse} onPass={onPass} />
      )}
    </span>
  );
}
