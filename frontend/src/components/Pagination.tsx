import styles from "./Pagination.module.css";

type Props = { page: number; limit: number; total: number; onPage: (page: number) => void };

export function Pagination({ page, limit, total, onPage }: Props) {
  if (total <= limit) return null;
  const pages = Math.ceil(total / limit);
  const from = (page - 1) * limit + 1;
  const to = Math.min(page * limit, total);
  return (
    <nav className={styles.nav} aria-label="Pages">
      <button className="ghost small" disabled={page <= 1} onClick={() => onPage(page - 1)}>← Previous</button>
      <span className="micro" aria-live="polite">{from}–{to} of {total} · page {page}/{pages}</span>
      <button className="ghost small" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next →</button>
    </nav>
  );
}
