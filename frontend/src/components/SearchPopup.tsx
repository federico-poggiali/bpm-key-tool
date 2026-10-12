import { useEffect, useRef } from "react";
import SearchPage from "../pages/SearchPage";
import styles from "./SearchPopup.module.css";

/** Library search: a popup over the page; following any result closes it. */
export function SearchPopup({ onClose }: { onClose: () => void }) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className={styles.backdrop} onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={panel} className={styles.panel} role="dialog" aria-modal="true" aria-label="Search your library"
        onClick={(e) => (e.target as HTMLElement).closest("a") && onClose()}>
        <button type="button" className={`ghost small ${styles.close}`} onClick={onClose}>Close</button>
        <SearchPage embedded />
      </div>
    </div>
  );
}
