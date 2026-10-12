import { useEffect, useId, useState } from "react";
import type { LabelData, LabelTrack } from "../api/api";
import styles from "./LabelEditor.module.css";

type MainHidden = NonNullable<LabelData["hidden"]>[number];
type TrackHidden = NonNullable<LabelTrack["hidden"]>[number];

export const parseList = (text: string) => text.split(",").map((s) => s.trim()).filter(Boolean);
const sameList = (a: string[], b: string[]) => a.length === b.length && a.every((v, i) => v === b[i]);

function toggled<T>(list: T[] | undefined, item: T, on: boolean): T[] {
  const rest = (list ?? []).filter((x) => x !== item);
  return on ? rest : [...rest, item];
}

type FieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** The "print" tick: unticked hides the field from the label. */
  printed?: boolean;
  onPrinted?: (on: boolean) => void;
  multiline?: boolean;
  hint?: string;
  /** Accessible name when the visible label is not unique (one per track). */
  name?: string;
};

function Field({ label, value, onChange, printed, onPrinted, multiline, hint, name = label }: FieldProps) {
  const id = useId();
  const Control = multiline ? "textarea" : "input";
  return (
    <div className={styles.field}>
      <label htmlFor={id} className="micro">{label}</label>
      <Control
        id={id} className="field-input" value={value} placeholder={hint} aria-label={name}
        onChange={(e) => onChange(e.target.value)}
        {...(multiline ? { rows: 2 } : {})}
      />
      {onPrinted ? (
        <input type="checkbox" className={styles.print} checked={printed} aria-label={`Print ${name.toLowerCase()}`}
          title={printed ? "Printed" : "Hidden"} onChange={(e) => onPrinted(e.target.checked)} />
      ) : <span />}
    </div>
  );
}

/** A comma-separated list. Keeps what is being typed (a trailing comma) until it is a real item. */
function ListField({ value, onChange, ...rest }: Omit<FieldProps, "value" | "onChange"> & { value: string[]; onChange: (v: string[]) => void }) {
  const [text, setText] = useState(value.join(", "));
  useEffect(() => {
    if (!sameList(parseList(text), value)) setText(value.join(", "));
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps
  return <Field {...rest} value={text} onChange={(t) => { setText(t); onChange(parseList(t)); }} />;
}

type Props = { value: LabelData; onChange: (next: LabelData) => void; /** A label with no record behind it: tracks can be added, renamed and removed. */ loose?: boolean };

export function LabelEditor({ value, onChange, loose }: Props) {
  const set = <K extends keyof LabelData>(key: K, v: LabelData[K]) => onChange({ ...value, [key]: v });
  const text = (key: "label" | "catno" | "year" | "country" | "note") => (v: string) => set(key, v === "" ? null : v);
  const shown = (field: MainHidden) => !(value.hidden ?? []).includes(field);
  const printed = (field: MainHidden) => (on: boolean) => set("hidden", toggled(value.hidden, field, on));
  const setTrack = (i: number, patch: Partial<LabelTrack>) =>
    set("tracks", (value.tracks ?? []).map((t, n) => (n === i ? { ...t, ...patch } : t)));

  return (
    <div className={styles.editor}>
      <section aria-label="Main label" className={styles.group}>
        <h2>Main label</h2>
        <Field label="Artist" value={value.artist} onChange={(v) => set("artist", v)} />
        <Field label="Label" value={value.label ?? ""} onChange={text("label")} printed={shown("label")} onPrinted={printed("label")} />
        <Field label="Cat#" value={value.catno ?? ""} onChange={text("catno")} printed={shown("catno")} onPrinted={printed("catno")} />
        <Field label="Title" value={value.title} onChange={(v) => set("title", v)} />
        <Field label="Year" value={value.year ?? ""} onChange={text("year")} printed={shown("year")} onPrinted={printed("year")} />
        <Field label="Country" value={value.country ?? ""} onChange={text("country")} printed={shown("country")} onPrinted={printed("country")}
          hint="Not stored: type it if you want it" />
        <ListField label="Styles" value={value.styles ?? []} onChange={(v) => set("styles", v)} printed={shown("styles")} onPrinted={printed("styles")}
          hint="Comma separated" />
        <Field label="Note" value={value.note ?? ""} onChange={text("note")} printed={shown("note")} onPrinted={printed("note")} multiline
          hint="One sentence" />
        {value.qr_url && (
          <div className={styles.field}>
            <span className="micro">QR code</span>
            <span className={styles.qr}>{value.qr_url}</span>
            <input type="checkbox" className={styles.print} checked={shown("qr")} aria-label="Print qr code" onChange={(e) => printed("qr")(e.target.checked)} />
          </div>
        )}
      </section>

      <section aria-label="Tracks label" className={styles.group}>
        <h2>Tracks label</h2>
        {(value.tracks ?? []).length === 0 && <p className={styles.empty}>{loose ? "No tracks yet." : "This record has no tracks."}</p>}
        {(value.tracks ?? []).map((t, i) => {
          const trackShown = (f: TrackHidden) => !(t.hidden ?? []).includes(f);
          const trackPrinted = (f: TrackHidden) => (on: boolean) => setTrack(i, { hidden: toggled(t.hidden, f, on) });
          return (
            <fieldset key={i} className={styles.track} data-skipped={t.skip || undefined}>
              <legend>
                <label className={styles.include}>
                  <input type="checkbox" checked={!t.skip} onChange={(e) => setTrack(i, { skip: !e.target.checked })}
                    aria-label={`Include track ${t.position}`} />
                  {loose ? null : <span className="mono">{t.position}</span>}
                </label>
                {loose && (
                  <>
                    <input className="field-input" aria-label={`Position of track ${i + 1}`} value={t.position} size={4}
                      onChange={(e) => setTrack(i, { position: e.target.value })} />
                    <button type="button" className="ghost small" aria-label={`Remove track ${t.position}`}
                      onClick={() => set("tracks", (value.tracks ?? []).filter((_, n) => n !== i))}>Remove</button>
                  </>
                )}
              </legend>
              <div className={styles.trackFields}>
                <Field label="BPM" name={`BPM ${t.position}`} value={t.bpm ?? ""} onChange={(v) => setTrack(i, { bpm: v || null })} printed={trackShown("bpm")} onPrinted={trackPrinted("bpm")} />
                <Field label="Key" name={`Key ${t.position}`} value={t.key ?? ""} onChange={(v) => setTrack(i, { key: v || null })} printed={trackShown("key")} onPrinted={trackPrinted("key")} />
                <ListField label="Tags" name={`Tags ${t.position}`} value={t.tags ?? []} onChange={(v) => setTrack(i, { tags: v })} printed={trackShown("tags")} onPrinted={trackPrinted("tags")} />
                <Field label="Note" name={`Note ${t.position}`} value={t.note ?? ""} onChange={(v) => setTrack(i, { note: v || null })} printed={trackShown("note")} onPrinted={trackPrinted("note")} />
              </div>
            </fieldset>
          );
        })}
        {loose && (
          <button type="button" className="ghost" onClick={() => set("tracks", [...(value.tracks ?? []), { position: nextPosition(value.tracks ?? []), skip: false, tags: [], hidden: [] }])}>
            Add track
          </button>
        )}
      </section>
    </div>
  );
}

/** A1, A2, ... then B1: carries on from the last track's side. */
function nextPosition(tracks: LabelTrack[]) {
  const last = tracks[tracks.length - 1]?.position ?? "";
  const m = /^([A-Za-z]*)(\d*)$/.exec(last);
  if (!m || !m[1]) return tracks.length === 0 ? "A1" : String(tracks.length + 1);
  return `${m[1]}${(Number(m[2]) || 0) + 1}`;
}
