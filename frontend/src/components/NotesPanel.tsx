import { useMemo, useState, type FormEvent } from "react";
import type { NoteOut, RecordDetail } from "../api/api";
import { useNoteMutations } from "../hooks";
import { NOTE_TYPES } from "../lib";
import { NoteEditor } from "./NoteEditor";
import styles from "./NotesPanel.module.css";

export function NotesPanel({ record }: { record: RecordDetail }) {
  const { create, patch, remove } = useNoteMutations(record.id);
  const [type, setType] = useState("prose");
  const [target, setTarget] = useState("record");
  const [body, setBody] = useState("");

  const items = useMemo(() => {
    const all: { note: NoteOut; target: string }[] = [
      ...record.notes.map((note) => ({ note, target: "Record" })),
      ...record.tracks.flatMap((t) => t.notes.map((note) => ({ note, target: `${t.position} ${t.title}`.trim() }))),
    ];
    const groups = new Map<string, typeof all>();
    for (const item of all) groups.set(item.note.type, [...(groups.get(item.note.type) ?? []), item]);
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [record]);

  const suggestions = useMemo(() => [...new Set([...NOTE_TYPES, ...items.map(([t]) => t)])], [items]);

  const add = (e: FormEvent) => {
    e.preventDefault();
    if (!body.trim() || !type.trim()) return;
    create.mutate(
      { type: type.trim(), body, record_id: target === "record" ? record.id : null, track_id: target === "record" ? null : Number(target) },
      { onSuccess: () => setBody("") },
    );
  };

  return (
    <section className={styles.panel} aria-label="Notes">
      <h2 className={styles.title}>Notes</h2>
      <form className={styles.add} onSubmit={add}>
        <div className={styles.row}>
          <label>
            <span className="micro">type</span>
            <input className="field-input" list="note-types" value={type} onChange={(e) => setType(e.target.value)} required />
          </label>
          <datalist id="note-types">{suggestions.map((t) => <option key={t} value={t} />)}</datalist>
          <label>
            <span className="micro">about</span>
            <select className="field-input" value={target} onChange={(e) => setTarget(e.target.value)}>
              <option value="record">The whole record</option>
              {record.tracks.map((t) => <option key={t.id} value={t.id}>{`${t.position} ${t.title}`.trim()}</option>)}
            </select>
          </label>
        </div>
        <label>
          <span className="micro">note (markdown)</span>
          <textarea className="field-input" rows={3} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Huge energy, the floor went off…" required />
        </label>
        <div><button className="primary" type="submit" disabled={create.isPending}>Add note</button></div>
      </form>

      {items.length === 0 && <p className={styles.empty}>No notes yet. Cue points, where it lives on the shelf, what the crowd did.</p>}
      {items.map(([groupType, group]) => (
        <div key={groupType} className={styles.group}>
          <h3 className="micro">{groupType} · {group.length}</h3>
          {group.map(({ note, target: label }) => (
            <NoteEditor
              key={note.id} note={note} target={label} typeSuggestions={suggestions}
              onSave={(draft) => patch.mutate({ id: note.id, body: draft })}
              onDelete={() => remove.mutate(note.id)}
            />
          ))}
        </div>
      ))}
    </section>
  );
}
