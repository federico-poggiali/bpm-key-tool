import { Link } from "react-router-dom";
import type { TagCount } from "../api/api";
import styles from "./TagEditor.module.css";

type Props = {
  tags: string[];
  /** Every tag designed in the Tag Manager; only these can be put on an item. */
  options: TagCount[];
  onAdd: (name: string) => void;
  onRemove: (name: string) => void;
  label: string;
};

export function TagEditor({ tags, options, onAdd, onRemove, label }: Props) {
  const free = options.filter((o) => !tags.includes(o.name));
  const groups = [...new Set(free.map((o) => o.group))];
  return (
    <div className={styles.wrap}>
      <ul className={styles.tags} aria-label={`${label} tags`}>
        {tags.map((tag) => (
          <li key={tag} className={styles.tag}>
            {tag}
            <button type="button" aria-label={`Remove tag ${tag}`} onClick={() => onRemove(tag)}>
              ×
            </button>
          </li>
        ))}
      </ul>
      {options.length === 0 ? (
        <Link className={styles.empty} to="/tags">Design tags in the Tag Manager</Link>
      ) : free.length > 0 && (
        <select className={`field-input ${styles.input}`} value="" aria-label={`Add a tag to ${label}`}
          onChange={(e) => e.target.value && onAdd(e.target.value)}>
          <option value="">add tag</option>
          {groups.map((g) => (
            <optgroup key={g} label={g}>
              {free.filter((o) => o.group === g).map((o) => <option key={o.name} value={o.name}>{o.name}</option>)}
            </optgroup>
          ))}
        </select>
      )}
    </div>
  );
}
