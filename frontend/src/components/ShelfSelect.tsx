import { useMemo } from "react";
import { placeLabel, type Place } from "../crate";

/** Pick a section of the shelf, grouped by unit; the empty value is Unsorted. */
export function ShelfSelect({ value, places, onChange, label, className }: {
  value: number | null; places: Map<number, Place>; onChange: (id: number | null) => void; label: string; className?: string;
}) {
  const groups = useMemo(() => {
    const out = new Map<string, Place[]>();
    for (const p of places.values()) out.set(p.unit.name, [...(out.get(p.unit.name) ?? []), p]);
    return [...out.entries()];
  }, [places]);
  return (
    <select className={className} aria-label={label} value={value ?? ""} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
      <option value="">Unsorted</option>
      {groups.map(([unit, ps]) => (
        <optgroup key={unit} label={unit}>
          {ps.map((p) => <option key={p.section.id} value={p.section.id}>{placeLabel(p).split(" › ").slice(1).join(" › ")}</option>)}
        </optgroup>
      ))}
    </select>
  );
}
