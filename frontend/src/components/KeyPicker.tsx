import { WHEEL_KEYS, type KeyFormat } from "../lib";
import styles from "./KeyPicker.module.css";

type Props = { value?: string; format: KeyFormat; onChange: (camelot: string | undefined) => void };

/** The Camelot wheel as two rows: minor (A) on top, major (B) below, 1 to 12 left to right. */
export function KeyPicker({ value, format, onChange }: Props) {
  const row = (letter: "A" | "B") =>
    WHEEL_KEYS.filter((k) => k.camelot.endsWith(letter)).sort((a, b) => parseInt(a.camelot) - parseInt(b.camelot));
  return (
    <div className={styles.wrap} role="group" aria-label="Key">
      {(["A", "B"] as const).map((letter) => (
        <div key={letter} className={styles.row}>
          {row(letter).map((k) => (
            <button
              key={k.camelot} type="button" className={styles.key} aria-pressed={value === k.camelot}
              title={`${k.camelot} · ${k.name}`} aria-label={`${k.camelot}, ${k.name}`}
              onClick={() => onChange(value === k.camelot ? undefined : k.camelot)}
            >
              {format === "camelot" ? k.camelot : k.short}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
