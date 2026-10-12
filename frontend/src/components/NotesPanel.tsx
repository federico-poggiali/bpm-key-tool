import { useMemo, useState, type FormEvent } from "react";
import type { NoteOut, RecordDetail } from "../api/api";
import { useNoteMutations } from "../hooks";
import { NoteEditor } from "./NoteEditor";
import styles from "./NotesPanel.module.css";

export function NotesPanel({ record }: { record: RecordDetail }) {
  const { create, patch, remove } = useNoteMutations(record.id);
  const [body, setBody] = useState("");

  const items: { note: NoteOut; target: string }[] = useMemo(() => [
    ...record.notes.map((note) => ({ note, target: "Record" })),
    ...record.tracks.flatMap((t) => t.notes.map((note) => ({ note, target: `${t.position} ${t.title}`.trim() }))),
  ], [record]);

  const add = (e: FormEvent) => {
    e.preventDefault();
    if (!body.trim()) return;
    create.mutate(
      { type: "prose", body, record_id: record.id, track_id: null },
      { onSuccess: () => setBody("") },
    );
  };

  return (
    <section className={styles.panel} aria-label="Notes">
      <h2 className={styles.title}>Notes</h2>
      <form className={styles.add} onSubmit={add}>
        <label>
          <span className="micro">note</span>
          <textarea className="field-input" rows={3} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Huge energy, the floor went off…" required />
        </label>
        <div><button className="primary" type="submit" disabled={create.isPending}>Add note</button></div>
      </form>

      {items.length === 0 && <p className={styles.empty}>No notes yet. Where it lives on the shelf, what the crowd did.</p>}
      {items.map(({ note, target: label }) => (
        <NoteEditor
          key={note.id} note={note} target={label}
          onSave={(draft) => patch.mutate({ id: note.id, body: draft })}
          onDelete={() => remove.mutate(note.id)}
        />
      ))}
    </section>
  );
}
