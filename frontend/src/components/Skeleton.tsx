import styles from "./Skeleton.module.css";

export function Skeleton({ rows = 4, height = 66 }: { rows?: number; height?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={styles.skel} style={{ height }} />
      ))}
    </div>
  );
}

export function SkeletonGrid({ count = 8 }: { count?: number }) {
  return (
    <div className={styles.grid} aria-busy="true" aria-label="Loading">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className={styles.card} />
      ))}
    </div>
  );
}
