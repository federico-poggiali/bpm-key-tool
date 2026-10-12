import { useEffect, useId, useRef, useState } from "react";
import type { NoteOut } from "../api/api";
import styles from "./NoteEditor.module.css";

export type NoteDraft = { body?: string };

type Props = {
  note: NoteOut;
  target: string;
  onSave: (patch: NoteDraft) => void;
  onDelete: () => void;
  defaultEditing?: boolean;
  debounceMs?: number;
};

/** One note. Editing autosaves shortly after you stop typing and shows when it has saved. */
export function NoteEditor({ note, target, onSave, onDelete, defaultEditing = false, debounceMs = 800 }: Props) {
  const [editing, setEditing] = useState(defaultEditing);
  const [body, setBody] = useState(note.body);
  const [state, setState] = useState<"idle" | "pending" | "saved">("idle");
  const [confirming, setConfirming] = useState(false);
  const id = useId();
  const latest = useRef({ body });
  const saved = useRef({ body: note.body });
  latest.current = { body };

  const flush = () => {
    const { body: b } = latest.current;
    if (b === saved.current.body) return setState("idle");
    saved.current = { body: b };
    onSave({ body: b });
    setState("saved");
  };

  useEffect(() => {
    if (!editing) return;
    if (body === saved.current.body) return;
    setState("pending");
    const timer = setTimeout(flush, debounceMs);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [body, editing, debounceMs]);

  // Pick up changes made elsewhere (e.g. after a refetch) while not editing.
  useEffect(() => {
    if (!editing) {
      setBody(note.body);
      saved.current = { body: note.body };
    }
  }, [note.body, editing]);

  return (
    <article id={`note-${note.id}`} className={styles.note} data-testid={`note-${note.id}`}>
      <header className={styles.head}>
        <span className={styles.target}>{target}</span>
        <span className={styles.status} aria-live="polite">
          {state === "pending" ? "Saving…" : state === "saved" ? "Saved" : ""}
        </span>
      </header>
      {editing ? (
        <div className={styles.form}>
          <label className="sr" htmlFor={`body-${id}`}>Note text</label>
          <textarea id={`body-${id}`} className="field-input" rows={5} value={body} onChange={(e) => setBody(e.target.value)} />
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
