import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import { placeLabel, placesOf } from "../crate";
import { ShelfSelect } from "./ShelfSelect";
import styles from "./ShelfPrompt.module.css";

/** Asks where a record that just joined the library goes on the shelf. Shows nothing when no shelf
    has been drawn yet or the record is already placed. */
export function ShelfPrompt({ recordId, onDone }: { recordId: number; onDone: () => void }) {
  const client = useQueryClient();
  const crate = useQuery({ queryKey: ["crate"], queryFn: api.getCrate });
  const places = useMemo(() => placesOf(crate.data?.units ?? []), [crate.data]);
  const record = crate.data?.unsorted.find((r) => r.id === recordId);
  const suggested = record?.suggestion ? places.get(record.suggestion.section_id) : undefined;
  const [choice, setChoice] = useState<number | null>(null);
  const [filed, setFiled] = useState<string | null>(null);
  const place = useMutation({
    mutationFn: (sectionId: number) => api.place([recordId], sectionId),
    onSuccess: (data, sectionId) => {
      client.setQueryData(["crate"], data);
      const p = placesOf(data.units).get(sectionId);
      setFiled(p ? placeLabel(p) : "the shelf");
    },
  });

  if (filed) {
    return (
      <p className={styles.done} role="status">
        Filed in <b>{filed}</b>. <Link to="/crate">See it on the shelf</Link>
        <button type="button" className="ghost small" onClick={onDone}>OK</button>
      </p>
    );
  }
  if (!crate.data || places.size === 0 || !record) return null;

  const picked = choice ?? record.suggestion?.section_id ?? null;
  return (
    <section className={styles.card} aria-labelledby="shelf-prompt">
      <div className={styles.text}>
        <span className="micro">crate</span>
        <h2 id="shelf-prompt">Where does it go?</h2>
        {suggested && record.suggestion ? (
          <p>Suggested: <b>{placeLabel(suggested)}</b> <span className={styles.why}>matches {record.suggestion.reasons.join(", ")}</span></p>
        ) : (
          <p>Nothing on your shelf matches its styles or tags yet. Pick a cube.</p>
        )}
      </div>
      <div className={styles.actions}>
        <ShelfSelect className={`field-input ${styles.select}`} value={picked} places={places} label="Shelf spot" onChange={setChoice} />
        <button type="button" className="primary" disabled={picked == null || place.isPending} onClick={() => picked != null && place.mutate(picked)}>
          {place.isPending ? "Filing…" : "Put it here"}
        </button>
        <button type="button" className="ghost" onClick={onDone}>Later</button>
      </div>
    </section>
  );
}
