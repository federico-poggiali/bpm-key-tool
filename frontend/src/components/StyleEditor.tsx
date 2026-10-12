import { useId, useState } from "react";
import styles from "./TagEditor.module.css";

type Props = {
  styles: string[];
  suggestions: string[];
  manual: boolean;
  onChange: (styles: string[]) => void;
  onReset?: () => void;
  readOnly?: boolean;
};

/** Discogs styles on a record. Editing locks them against re-fetching; Reset gives Discogs' list back. */
export function StyleEditor({ styles: current, suggestions, manual, onChange, onReset, readOnly }: Props) {
  const [text, setText] = useState("");
  const listId = useId();
  const has = (name: string) => current.some((s) => s.toLowerCase() === name.toLowerCase());

  const commit = () => {
    const name = text.trim().replace(/\s+/g, " ").replace(/,+$/, "");
    setText("");
    if (name && !has(name)) onChange([...current, name]);
  };

  return (
    <div className={styles.wrap}>
      <span className="micro">styles</span>
      <ul className={styles.tags} aria-label="Styles">
        {current.map((s) => (
          <li key={s} className={styles.tag}>
            {s}
            {!readOnly && <button type="button" aria-label={`Remove style ${s}`} onClick={() => onChange(current.filter((x) => x !== s))}>×</button>}
          </li>
        ))}
      </ul>
      {readOnly ? <span className="micro">Open it from your library to edit styles.</span> : <input
        className={`field-input ${styles.input}`}
        value={text}
        list={listId}
        placeholder="add style"
        aria-label="Add a style"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            commit();
          }
        }}
        onBlur={() => text.trim() && commit()}
      />}
      <datalist id={listId}>
        {suggestions.filter((s) => !has(s)).map((s) => <option key={s} value={s} />)}
      </datalist>
      {manual && (
        <>
          <span className="micro" data-testid="styles-edited">edited</span>
          {onReset && <button type="button" className="ghost small" onClick={onReset}>Reset to Discogs</button>}
        </>
      )}
    </div>
  );
}
