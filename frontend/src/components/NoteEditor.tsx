import { useEffect, useId, useRef, useState } from "react";
import type { NoteOut } from "../api/api";
import styles from "./NoteEditor.module.css";

export type NoteDraft = { type?: string; body?: string };

type Props = {
  note: NoteOut;
  target: string;
  typeSuggestions: string[];
  onSave: (patch: NoteDraft) => void;
  onDelete: () => void;
  defaultEditing?: boolean;
  debounceMs?: number;
};

/** One note. Editing autosaves shortly after you stop typing and shows when it has saved. */
export function NoteEditor({ note, target, typeSuggestions, onSave, onDelete, defaultEditing = false, debounceMs = 800 }: Props) {
  const [editing, setEditing] = useState(defaultEditing);
  const [type, setType] = useState(note.type);
  const [body, setBody] = useState(note.body);
  const [state, setState] = useState<"idle" | "pending" | "saved">("idle");
  const [confirming, setConfirming] = useState(false);
  const listId = useId();
  const latest = useRef({ type, body });
  const saved = useRef({ type: note.type, body: note.body });
  latest.current = { type, body };

  const flush = () => {
    const { type: t, body: b } = latest.current;
    const patch: NoteDraft = {};
    if (t.trim() && t.trim() !== saved.current.type) patch.type = t.trim();
    if (b !== saved.current.body) patch.body = b;
    if (Object.keys(patch).length === 0) return setState("idle");
    saved.current = { type: patch.type ?? saved.current.type, body: patch.body ?? saved.current.body };
    onSave(patch);
    setState("saved");
  };

  useEffect(() => {
    if (!editing) return;
    if (type === saved.current.type && body === saved.current.body) return;
    setState("pending");
    const timer = setTimeout(flush, debounceMs);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, body, editing, debounceMs]);

  // Pick up changes made elsewhere (e.g. after a refetch) while not editing.
  useEffect(() => {
    if (!editing) {
      setType(note.type);
      setBody(note.body);
      saved.current = { type: note.type, body: note.body };
    }
  }, [note.type, note.body, editing]);

  return (
    <article id={`note-${note.id}`} className={styles.note} data-testid={`note-${note.id}`}>
      <header className={styles.head}>
        <span className={styles.type}>{note.type}</span>
        <span className={styles.target}>{target}</span>
        <span className={styles.status} aria-live="polite">
          {state === "pending" ? "Saving…" : state === "saved" ? "Saved" : ""}
        </span>
      </header>
      {editing ? (
        <div className={styles.form}>
          <label className="sr" htmlFor={`type-${listId}`}>Note type</label>
          <input id={`type-${listId}`} className="field-input" list={listId} value={type} onChange={(e) => setType(e.target.value)} />
          <datalist id={listId}>{typeSuggestions.map((t) => <option key={t} value={t} />)}</datalist>
          <label className="sr" htmlFor={`body-${listId}`}>Note text (markdown)</label>
          <textarea id={`body-${listId}`} className="field-input" rows={5} value={body} onChange={(e) => setBody(e.target.value)} />
        </div>
      ) : (
        <p className={styles.body}>{note.body}</p>
      )}
      <footer className={styles.actions}>
        <button className="ghost small" onClick={() => { if (editing) flush(); setEditing(!editing); }}>
          {editing ? "Done" : "Edit"}
        </button>
        {confirming ? (
          <>
            <button className="ghost small danger" onClick={onDelete}>Confirm delete</button>
            <button className="ghost small" onClick={() => setConfirming(false)}>Keep</button>
          </>
        ) : (
          <button className="ghost small danger" onClick={() => setConfirming(true)}>Delete</button>
        )}
      </footer>
    </article>
  );
}
