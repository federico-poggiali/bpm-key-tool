import { useState } from "react";
import type { TagCount } from "../api/api";
import styles from "./TagPicker.module.css";

type Props = { tags: TagCount[]; selected: string[]; onToggle: (name: string) => void };

export function TagPicker({ tags, selected, onToggle }: Props) {
  const [filter, setFilter] = useState("");
  const visible = tags.filter((t) => t.name.includes(filter.trim().toLowerCase()) || selected.includes(t.name));
  if (tags.length === 0) return <p className={styles.empty}>No tags yet.</p>;
  return (
    <div className={styles.wrap} role="group" aria-label="Tags">
      {tags.length > 12 && (
        <input className={`field-input ${styles.filter}`} placeholder="find a tag" aria-label="Find a tag" value={filter} onChange={(e) => setFilter(e.target.value)} />
      )}
      <ul className={styles.list}>
        {visible.map((t) => (
          <li key={t.name}>
            <button type="button" aria-pressed={selected.includes(t.name)} onClick={() => onToggle(t.name)}
              title={`${t.record_count} records · ${t.track_count} tracks`}>
              {t.name}<span>{t.record_count + t.track_count}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
