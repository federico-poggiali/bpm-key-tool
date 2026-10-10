import type { KeyFormat } from "../lib";
import styles from "./KeyFormatToggle.module.css";

export function KeyFormatToggle({ value, onChange }: { value: KeyFormat; onChange: (f: KeyFormat) => void }) {
  return (
    <div className={styles.toggle} role="group" aria-label="Key notation">
      {(["camelot", "musical"] as const).map((f) => (
        <button key={f} type="button" aria-pressed={value === f} onClick={() => onChange(f)}>
          {f === "camelot" ? "8A" : "Am"}
        </button>
      ))}
    </div>
  );
}
