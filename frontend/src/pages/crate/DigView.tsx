import { useState } from "react";
import type { CrateRecord, CubeOut, UnsortedRecord } from "../../api/api";
import { placeLabel, type Place } from "../../crate";
import styles from "./crate.module.css";
import { DRAG_TYPE, matches, RecordRow, type PlaceRecord } from "./common";

/** Records you own that are not on the shelf yet, to drag onto a cube. */
export function Tray({ records, places, onPlace }: { records: UnsortedRecord[]; places: Map<number, Place>; onPlace: PlaceRecord }) {
  const [filter, setFilter] = useState("");
  const [over, setOver] = useState(false);
  const f = filter.trim().toLowerCase();
  const shown = f ? records.filter((r) => matches(r, f) || r.styles.some((s) => s.toLowerCase().includes(f)) || r.tags.some((t) => t.includes(f))) : records;
  return (
    <div className={`${styles.card} ${over ? styles.over : ""}`}
      onDragOver={(e) => { if (e.dataTransfer.types.includes(DRAG_TYPE)) { e.preventDefault(); setOver(true); } }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { setOver(false); const id = Number(e.dataTransfer.getData(DRAG_TYPE)); if (id) onPlace(id, null); }}>
      <div className={styles.cardHead}>
        <h2>Unsorted</h2>
        <span className={styles.count} data-testid="unsorted-count">{records.length}</span>
      </div>
      <p className={styles.hint}>Drag a record onto a cube, or pick where it goes. Suggestions match its tags and styles against your cube names and descriptions.</p>
      {records.length > 0 && <input className="field-input" type="search" placeholder="Filter by artist, title, style, tag" aria-label="Filter unsorted records" value={filter} onChange={(e) => setFilter(e.target.value)} />}
      {records.length === 0 ? (
        <p className={styles.hint}>Every record you own is on the shelf.</p>
      ) : (
        <ul className={styles.rows} aria-label="Unsorted records">
          {shown.slice(0, 200).map((r) => {
            const hint = r.suggestion ? places.get(r.suggestion.section_id) : undefined;
            return (
              <RecordRow key={r.id} record={r} sectionId={null} places={places} onPlace={onPlace}>
                {hint && r.suggestion && (
                  <button type="button" className={styles.suggest} onClick={() => onPlace(r.id, r.suggestion!.section_id)}
                    title={`Matches ${r.suggestion.reasons.join(", ")}`}>
                    → {placeLabel(hint)} <em>{r.suggestion.reasons.join(", ")}</em>
                  </button>
                )}
              </RecordRow>
            );
          })}
          {shown.length > 200 && <li className={styles.hint}>{shown.length - 200} more. Filter to narrow down.</li>}
        </ul>
      )}
    </div>
  );
}

export function FindResults({ found, unsortedHits, onShow }: { found: { record: CrateRecord; place: Place }[]; unsortedHits: CrateRecord[]; onShow: (c: CubeOut) => void }) {
  return (
    <div className={styles.card} role="status">
      <div className={styles.cardHead}>
        <h2>Found</h2>
        <span className={styles.count}>{found.length + unsortedHits.length}</span>
      </div>
      <ul className={styles.found}>
        {found.slice(0, 30).map(({ record, place }) => (
          <li key={record.id}>
            <button type="button" onClick={() => onShow(place.cube)}>
              <b>{record.artist} – {record.title}</b>
              <span>{placeLabel(place)}</span>
            </button>
          </li>
        ))}
        {unsortedHits.slice(0, 10).map((r) => (
          <li key={r.id}><span className={styles.foundOff}><b>{r.artist} – {r.title}</b><span>not on the shelf yet</span></span></li>
        ))}
        {found.length + unsortedHits.length === 0 && <li className={styles.hint}>Nothing you own matches.</li>}
      </ul>
    </div>
  );
}
