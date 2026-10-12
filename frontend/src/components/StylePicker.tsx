import { useState } from "react";
import type { StyleCount } from "../api/api";
import styles from "./TagPicker.module.css";

type Props = { styles: StyleCount[]; selected: string[]; onToggle: (name: string) => void };

/** Same pattern as TagPicker; styles match case-insensitively, as the API does. */
export function StylePicker({ styles: counts, selected, onToggle }: Props) {
  const [filter, setFilter] = useState("");
  const isOn = (name: string) => selected.some((s) => s.toLowerCase() === name.toLowerCase());
  const visible = counts.filter((s) => s.name.toLowerCase().includes(filter.trim().toLowerCase()) || isOn(s.name));
  if (counts.length === 0) return <p className={styles.empty}>No styles yet. Add records, or fetch styles in Settings.</p>;
  return (
    <div className={styles.wrap} role="group" aria-label="Styles">
      {counts.length > 12 && (
        <input className={`field-input ${styles.filter}`} placeholder="find a style" aria-label="Find a style" value={filter} onChange={(e) => setFilter(e.target.value)} />
      )}
      <ul className={styles.list}>
        {visible.map((s) => (
          <li key={s.name}>
            <button type="button" aria-pressed={isOn(s.name)} onClick={() => onToggle(s.name)} title={`${s.record_count} records`}>
              {s.name}<span>{s.record_count}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
