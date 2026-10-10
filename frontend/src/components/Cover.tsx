import styles from "./Cover.module.css";

export function Cover({ url, size, alt = "" }: { url?: string | null; size?: number; alt?: string }) {
  const style = size ? { width: size, height: size } : undefined;
  return url ? (
    <img className={styles.cover} src={url} alt={alt} style={style} loading="lazy" referrerPolicy="no-referrer" />
  ) : (
    <div className={`${styles.cover} ${styles.empty}`} style={style} role="img" aria-label={alt || "No cover"}>
      <i /><i /><i />
    </div>
  );
}
