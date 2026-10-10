import { useEffect, useId, useRef, useState } from "react";
import { BPM_MAX, BPM_MIN } from "../libraryParams";
import styles from "./BpmRange.module.css";

type Props = { min?: number; max?: number; onChange: (range: { bpmMin?: number; bpmMax?: number }) => void; delay?: number };

/** Two-handle BPM slider. The ends of the track mean "no limit". */
export function BpmRange({ min, max, onChange, delay = 250 }: Props) {
  const id = useId();
  const [lo, setLo] = useState(min ?? BPM_MIN);
  const [hi, setHi] = useState(max ?? BPM_MAX);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    clearTimeout(timer.current); // the URL changed (back button, clear): it wins over a pending edit
    setLo(min ?? BPM_MIN);
    setHi(max ?? BPM_MAX);
  }, [min, max]);
  useEffect(() => () => clearTimeout(timer.current), []);

  const commit = (nextLo: number, nextHi: number) => {
    setLo(nextLo);
    setHi(nextHi);
    clearTimeout(timer.current);
    timer.current = setTimeout(
      () => onChange({ bpmMin: nextLo <= BPM_MIN ? undefined : nextLo, bpmMax: nextHi >= BPM_MAX ? undefined : nextHi }),
      delay,
    );
  };

  const pct = (v: number) => ((v - BPM_MIN) / (BPM_MAX - BPM_MIN)) * 100;
  const text = lo <= BPM_MIN && hi >= BPM_MAX ? "any tempo" : `${lo <= BPM_MIN ? "≤" : lo}${lo > BPM_MIN && hi < BPM_MAX ? "–" : ""}${hi >= BPM_MAX ? "+" : hi}`;

  return (
    <div className={styles.wrap} role="group" aria-labelledby={`${id}-label`}>
      <div className={styles.top}>
        <span id={`${id}-label`} className="micro">bpm</span>
        <output className={styles.out}>{text}</output>
      </div>
      <div className={styles.track}>
        <div className={styles.fill} style={{ left: `${pct(lo)}%`, right: `${100 - pct(hi)}%` }} />
        <input type="range" aria-label="Minimum BPM" min={BPM_MIN} max={BPM_MAX} step={1} value={lo}
          onChange={(e) => commit(Math.min(Number(e.target.value), hi), hi)} />
        <input type="range" aria-label="Maximum BPM" min={BPM_MIN} max={BPM_MAX} step={1} value={hi}
          onChange={(e) => commit(lo, Math.max(Number(e.target.value), lo))} />
      </div>
    </div>
  );
}
