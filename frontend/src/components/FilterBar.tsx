import { useState, type ReactNode } from "react";
import type { StyleCount, TagCount } from "../api/api";
import type { KeyFormat } from "../lib";
import { isFiltered, type Filters, type View } from "../libraryParams";
import type { Status } from "../api/api";
import { KeyFormatToggle } from "./KeyFormatToggle";
import { KeyPicker } from "./KeyPicker";
import { StylePicker } from "./StylePicker";
import { TagPicker } from "./TagPicker";
import styles from "./FilterBar.module.css";

type Props = {
  filters: Filters;
  defaultStatus: Status;
  tags: TagCount[];
  styleCounts: StyleCount[];
  keyFormat: KeyFormat;
  onKeyFormat: (f: KeyFormat) => void;
  onChange: (patch: Partial<Filters>) => void;
  onClear: () => void;
  onOpenSearch: () => void;
};

// Mode: what the library lists. View: how records are laid out (tracks are always a table).
const MODES = [{ id: "records", label: "Records" }, { id: "tracks", label: "Tracks" }] as const;
const VIEWS: { id: View; label: string }[] = [
  { id: "grid", label: "Grid" },
  { id: "table", label: "Table" },
];

export function FilterBar({ filters, defaultStatus, tags, styleCounts, keyFormat, onKeyFormat, onChange, onClear, onOpenSearch }: Props) {
  const tracksView = filters.view === "tracks"; // BPM and key belong to tracks, not records

  const [pinned, setPinned] = useState<string | null>(null);
  const toggleStyle = (name: string) => {
    const on = filters.styles.some((s) => s.toLowerCase() === name.toLowerCase());
    onChange({ styles: on ? filters.styles.filter((s) => s.toLowerCase() !== name.toLowerCase()) : [...filters.styles, name] });
  };

  // Each menu row opens its picker in a flyout beside the rail on hover or focus; clicking pins it open.
  const menu = (id: string, label: string, active: string, body: ReactNode) => (
    <div className={`${styles.item} ${pinned === id ? styles.pinned : ""}`}
      onKeyDown={(e) => { if (e.key === "Escape") setPinned(null); }}>
      <button type="button" className={styles.trigger} aria-expanded={pinned === id} aria-label={label} title={`${label}: ${active}`}
        onClick={() => setPinned(pinned === id ? null : id)}>
        <span>{label}</span>
        <span className={styles.active} aria-hidden>{active}</span>
      </button>
      <div className={styles.flyout} role="group" aria-label={label}>{body}</div>
    </div>
  );
  const summary = (xs: string[]) => (xs.length === 0 ? "any" : xs.length === 1 ? xs[0] : `${xs.length} on`);

  return (
    <aside className={styles.bar} aria-label="Filters" onMouseLeave={() => setPinned(null)}>
      <div className={styles.modes} role="group" aria-label="Show">
        {MODES.map((m) => (
          <button key={m.id} type="button" aria-pressed={(m.id === "tracks") === tracksView}
            onClick={() => onChange({ view: m.id === "tracks" ? "tracks" : "grid" })}>{m.label}</button>
        ))}
      </div>
      <label className={styles.search}>
        <span className="sr">Search the library</span>
        <input type="search" readOnly placeholder="Search" value="" onClick={onOpenSearch} onFocus={onOpenSearch} />
      </label>
      {!tracksView && (
        <div className={styles.views} role="group" aria-label="View">
          {VIEWS.map((v) => (
            <button key={v.id} type="button" aria-pressed={filters.view === v.id} onClick={() => onChange({ view: v.id })}>{v.label}</button>
          ))}
        </div>
      )}
      <nav className={styles.menu} aria-label="Filter menu">
        {menu("styles", "Styles", summary(filters.styles),
          <StylePicker styles={styleCounts} selected={filters.styles} onToggle={toggleStyle} />)}
        {menu("tags", "Tags", summary(filters.tags),
          <TagPicker tags={tags} selected={filters.tags}
            onToggle={(name) => onChange({ tags: filters.tags.includes(name) ? filters.tags.filter((t) => t !== name) : [...filters.tags, name] })} />)}
        {tracksView && menu("key", "Key", filters.key ?? "any",
          <div className={styles.keys}>
            <div className={styles.keysHead}>
              <span className="micro">key</span>
              <KeyFormatToggle value={keyFormat} onChange={onKeyFormat} />
            </div>
            <KeyPicker value={filters.key} format={keyFormat} onChange={(key) => onChange({ key })} />
          </div>)}
      </nav>
      {isFiltered(filters, defaultStatus) && (
        <button type="button" className="ghost small" onClick={onClear}>Clear filters</button>
      )}
    </aside>
  );
}
