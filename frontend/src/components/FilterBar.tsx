import { useEffect, useRef, useState } from "react";
import type { TagCount } from "../api/api";
import type { KeyFormat } from "../lib";
import { isFiltered, type Filters, type View } from "../libraryParams";
import type { Status } from "../api/api";
import { BpmRange } from "./BpmRange";
import { KeyFormatToggle } from "./KeyFormatToggle";
import { KeyPicker } from "./KeyPicker";
import { TagPicker } from "./TagPicker";
import styles from "./FilterBar.module.css";

type Props = {
  filters: Filters;
  defaultStatus: Status;
  tags: TagCount[];
  keyFormat: KeyFormat;
  onKeyFormat: (f: KeyFormat) => void;
  onChange: (patch: Partial<Filters>) => void;
  onClear: () => void;
};

const VIEWS: { id: View; label: string }[] = [
  { id: "grid", label: "Grid" },
  { id: "table", label: "Table" },
  { id: "tracks", label: "Tracks" },
];

export function FilterBar({ filters, defaultStatus, tags, keyFormat, onKeyFormat, onChange, onClear }: Props) {
  const [text, setText] = useState(filters.q);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => {
    clearTimeout(timer.current);
    setText(filters.q);
  }, [filters.q]);
  useEffect(() => () => clearTimeout(timer.current), []);

  const onSearch = (value: string) => {
    setText(value);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => onChange({ q: value.trim() }), 300);
  };

  return (
    <section className={styles.bar} aria-label="Filters">
      <div className={styles.top}>
        <label className={styles.search}>
          <span className="sr">Search the library</span>
          <input type="search" placeholder="Search artist, title, label, notes" value={text} onChange={(e) => onSearch(e.target.value)} />
        </label>
        <div className={styles.views} role="group" aria-label="View">
          {VIEWS.map((v) => (
            <button key={v.id} type="button" aria-pressed={filters.view === v.id} onClick={() => onChange({ view: v.id })}>{v.label}</button>
          ))}
        </div>
      </div>
      <div className={styles.grid}>
        <BpmRange min={filters.bpmMin} max={filters.bpmMax} onChange={onChange} />
        <label className={styles.status}>
          <span className="micro">status</span>
          <select className="field-input" value={filters.status} onChange={(e) => onChange({ status: e.target.value as Filters["status"] })}>
            <option value="all">All</option>
            <option value="owned">Owned</option>
            <option value="wantlist">Wantlist</option>
            <option value="considering">Considering</option>
          </select>
        </label>
        <div className={styles.keys}>
          <div className={styles.keysHead}>
            <span className="micro">key</span>
            <KeyFormatToggle value={keyFormat} onChange={onKeyFormat} />
          </div>
          <KeyPicker value={filters.key} format={keyFormat} onChange={(key) => onChange({ key })} />
        </div>
      </div>
      <div className={styles.tags}>
        <span className="micro">tags</span>
        <TagPicker
          tags={tags} selected={filters.tags}
          onToggle={(name) => onChange({ tags: filters.tags.includes(name) ? filters.tags.filter((t) => t !== name) : [...filters.tags, name] })}
        />
      </div>
      {isFiltered(filters, defaultStatus) && (
        <button type="button" className="ghost small" onClick={onClear}>Clear filters</button>
      )}
    </section>
  );
}
