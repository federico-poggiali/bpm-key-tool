import { useId, useState } from "react";
import styles from "./TagEditor.module.css";

type Props = {
  tags: string[];
  suggestions: string[];
  onAdd: (name: string) => void;
  onRemove: (name: string) => void;
  label: string;
};

export function TagEditor({ tags, suggestions, onAdd, onRemove, label }: Props) {
  const [text, setText] = useState("");
  const listId = useId();

  const commit = () => {
    const name = text.trim().toLowerCase().replace(/,+$/, "");
    setText("");
    if (name && !tags.includes(name)) onAdd(name);
  };

  return (
    <div className={styles.wrap}>
      <ul className={styles.tags} aria-label={`${label} tags`}>
        {tags.map((tag) => (
          <li key={tag} className={styles.tag}>
            {tag}
            <button type="button" aria-label={`Remove tag ${tag}`} onClick={() => onRemove(tag)}>
              ×
            </button>
          </li>
        ))}
      </ul>
      <input
        className={`field-input ${styles.input}`}
        value={text}
        list={listId}
        placeholder="add tag"
        aria-label={`Add a tag to ${label}`}
        onChange={(e) => {
          const value = e.target.value;
          if (value.endsWith(",")) {
            setText(value);
            setTimeout(commit, 0);
          } else setText(value);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commit();
          }
        }}
        onBlur={() => text.trim() && commit()}
      />
      <datalist id={listId}>
        {suggestions.filter((s) => !tags.includes(s)).map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
    </div>
  );
}
