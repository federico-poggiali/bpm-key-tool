import { dismissToast, useToasts } from "../toast";
import styles from "./Toasts.module.css";

export function Toasts() {
  const toasts = useToasts();
  return (
    <div className={styles.stack} role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`${styles.toast} ${t.kind === "error" ? styles.error : ""}`}>
          <span>{t.message}</span>
          <button aria-label="Dismiss" onClick={() => dismissToast(t.id)}>
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
