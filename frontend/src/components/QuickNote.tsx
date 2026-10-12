import { useEffect, useId, useRef, useState } from "react";
import { useNoteMutations, useRecord } from "../hooks";
import styles from "./QuickNote.module.css";

/** A note on a corner: the small icon opens a dark pad, and what you write there
 *  is the record's note, the one that prints on its label. */
export function NoteDoodle({ filled, size = 18 }: { filled: boolean; size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 4h14v12l-4 4H5Z" />
      <path d="M15 20v-4h4M8 9h8M8 13h4" />
      {filled && <circle cx="19" cy="4.5" r="2.6" fill="var(--signal)" stroke="none" />}
    </svg>
  );
}

type Props = {
  recordId: number;
  title: string;
  filled: boolean;
  /** Set to write a track's note instead of the record's; its notes are already in hand. */
  track?: { id: number; notes: { id: number; body: string }[] };
  /** "hero": a big doodle with a caption, for the top of a record page. */
  variant?: "corner" | "hero";
  debounceMs?: number;
};

export function QuickNote({ recordId, title, filled, track, variant = "corner", debounceMs = 700 }: Props) {
  const [open, setOpen] = useState(false);
  const fetched = useRecord(open && !track ? recordId : 0);
  const record = track ? { data: { notes: track.notes }, isLoading: false } : fetched;
  const { create, patch, remove } = useNoteMutations(recordId);
  const existing = record.data?.notes[0];
  const [text, setText] = useState("");
  const [state, setState] = useState<"idle" | "pending" | "saved">("idle");
  const loaded = useRef(false);
  const saved = useRef("");
  const noteId = useRef<number | null>(null);
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const area = useRef<HTMLTextAreaElement>(null);
  const root = useRef<HTMLSpanElement>(null);
  const padId = useId();

  // Fill the pad once, when the record arrives.
  useEffect(() => {
    if (!open) { loaded.current = false; return; }
    if (!record.data || loaded.current) return;
    loaded.current = true;
    noteId.current = existing?.id ?? null;
    saved.current = existing?.body ?? "";
    setText(saved.current);
    area.current?.focus();
  }, [open, record.data, existing]);

  const flush = (body: string) => {
    if (body === saved.current) return setState("idle");
    saved.current = body;
    // One write at a time, so a note being created is never created twice.
    queue.current = queue.current.then(async () => {
      if (noteId.current == null) {
        if (!body.trim()) return;
        const made = await create.mutateAsync({ type: "prose", body, record_id: track ? null : recordId, track_id: track?.id ?? null });
        noteId.current = made.id;
      } else if (!body.trim()) {
        const id = noteId.current;
        noteId.current = null;
        await remove.mutateAsync(id);
      } else {
        await patch.mutateAsync({ id: noteId.current, body: { body } });
      }
      setState("saved");
    }).catch(() => setState("idle"));
  };

  useEffect(() => {
    if (!open || !loaded.current || text === saved.current) return;
    setState("pending");
    const timer = setTimeout(() => flush(text), debounceMs);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, open, debounceMs]);

  const close = () => { if (loaded.current) flush(text); setOpen(false); };

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) close(); };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, text]);

  return (
    <span className={`${styles.root} ${variant === "hero" ? styles.hero : ""}`} ref={root}>
      <button type="button" className={styles.doodle} data-filled={filled} aria-expanded={open} aria-controls={open ? padId : undefined}
        aria-label={`${filled ? "Edit note" : "Add a note"} for ${title}`} title={filled ? "Edit note" : "Add a note"}
        onClick={() => (open ? close() : setOpen(true))}>
        <NoteDoodle filled={filled} size={variant === "hero" ? 18 : 18} />
        {variant === "hero" && <span className={styles.caption}>{filled ? "Edit note" : "Add note"}</span>}
      </button>
      {open && (
        <div id={padId} className={styles.pad} role="dialog" aria-label={`Note for ${title}`}
          onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); close(); } }}>
          <textarea ref={area} className={styles.area} value={text} onChange={(e) => setText(e.target.value)}
            placeholder={record.isLoading ? "…" : "A line for the label. What it did to the floor."}
            aria-label="Note" disabled={record.isLoading} rows={5} />
          <div className={styles.foot}>
            <span className={styles.hint}>Prints on the label</span>
            <span className={styles.status} aria-live="polite">{state === "pending" ? "Saving…" : state === "saved" ? "Saved" : ""}</span>
            <button type="button" className="ghost small" onClick={close}>Done</button>
          </div>
        </div>
      )}
    </span>
  );
}
