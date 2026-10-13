import { useState } from "react";
import { api, type UnitOut } from "../../api/api";
import styles from "./crate.module.css";
import { cubeCount, Inline, MAX_X, MAX_Y, overlaps, type Act } from "./common";

const PRESETS = [
  { label: "1×1", rows: 1, cols: 1 },
  { label: "1×4", rows: 1, cols: 4 },
  { label: "2×2", rows: 2, cols: 2 },
  { label: "2×4", rows: 2, cols: 4 },
  { label: "4×4", rows: 4, cols: 4 },
  { label: "5×5", rows: 5, cols: 5 },
];

/** The first free spot for a new unit, scanning the wall row by row. */
function freeSpot(units: UnitOut[], rows: number, cols: number) {
  for (let y = 0; y <= MAX_Y; y++)
    for (let x = 0; x <= MAX_X; x++)
      if (!units.some((u) => overlaps({ x, y, rows, cols }, u))) return { x, y };
  return { x: 0, y: MAX_Y };
}

function SizeFields({ rows, cols, onChange }: { rows: number; cols: number; onChange: (rows: number, cols: number) => void }) {
  const clamp = (n: number) => Math.min(8, Math.max(1, Math.round(n) || 1));
  return (
    <div className={styles.size}>
      <label><span className="micro">rows</span><input className="field-input" type="number" min={1} max={8} value={rows} onChange={(e) => onChange(clamp(+e.target.value), cols)} /></label>
      <span aria-hidden="true">×</span>
      <label><span className="micro">columns</span><input className="field-input" type="number" min={1} max={8} value={cols} onChange={(e) => onChange(rows, clamp(+e.target.value))} /></label>
    </div>
  );
}

export function AddUnit({ units, act }: { units: UnitOut[]; act: Act }) {
  const [name, setName] = useState(`Unit ${units.length + 1}`);
  const [size, setSize] = useState({ rows: 4, cols: 4 });
  const add = () => {
    const spot = freeSpot(units, size.rows, size.cols);
    act(() => api.createUnit({ name: name.trim() || `Unit ${units.length + 1}`, ...size, ...spot }));
    setName(`Unit ${units.length + 2}`);
  };
  return (
    <form className={styles.card} onSubmit={(e) => { e.preventDefault(); add(); }}>
      <div className={styles.cardHead}><h2>Add a unit</h2></div>
      <p className={styles.hint}>A unit is one piece of furniture, like a Kallax or an Eket, made of cubes.</p>
      <label className={styles.field}>
        <span className="micro">name</span>
        <input className="field-input" value={name} onChange={(e) => setName(e.target.value)} maxLength={60} />
      </label>
      <div className={styles.presets} role="group" aria-label="Size presets">
        {PRESETS.map((p) => (
          <button key={p.label} type="button" className={`ghost small ${p.rows === size.rows && p.cols === size.cols ? styles.on : ""}`}
            aria-pressed={p.rows === size.rows && p.cols === size.cols} onClick={() => setSize({ rows: p.rows, cols: p.cols })}>{p.label}</button>
        ))}
      </div>
      <SizeFields rows={size.rows} cols={size.cols} onChange={(rows, cols) => setSize({ rows, cols })} />
      <button className="primary" type="submit">Add unit</button>
    </form>
  );
}

export function UnitPanel({ unit, units, act, onClose }: { unit: UnitOut; units: UnitOut[]; act: Act; onClose: () => void }) {
  const [size, setSize] = useState({ rows: unit.rows, cols: unit.cols });
  const lost = unit.cubes.filter((c) => c.row >= size.rows || c.col >= size.cols).reduce((n, c) => n + cubeCount(c), 0);
  const changed = size.rows !== unit.rows || size.cols !== unit.cols;
  const blocked = changed && units.some((o) => o.id !== unit.id && overlaps({ ...unit, ...size }, o));
  const total = unit.cubes.reduce((n, c) => n + cubeCount(c), 0);
  return (
    <div className={styles.card}>
      <div className={styles.cardHead}>
        <h2>{unit.name}</h2>
        <button type="button" className="ghost small" onClick={onClose}>Close</button>
      </div>
      <label className={styles.field}>
        <span className="micro">name</span>
        <Inline key={unit.name} value={unit.name} label="Unit name" onSave={(name) => name && act(() => api.patchUnit(unit.id, { name }))} />
      </label>
      <SizeFields rows={size.rows} cols={size.cols} onChange={(rows, cols) => setSize({ rows, cols })} />
      {lost > 0 && <p className={styles.warn}>{lost} record{lost === 1 ? "" : "s"} in the removed cubes go back to Unsorted.</p>}
      {blocked && <p className={styles.warn}>At this size it would overlap another unit. Move it first.</p>}
      <div className={styles.actions}>
        <button type="button" className="primary" disabled={!changed || blocked} onClick={() => act(() => api.patchUnit(unit.id, size))}>Resize</button>
        <button type="button" className="ghost danger" onClick={() => {
          if (window.confirm(`Delete ${unit.name}?${total ? ` Its ${total} records go back to Unsorted.` : ""}`)) { act(() => api.deleteUnit(unit.id)); onClose(); }
        }}>Delete unit</button>
      </div>
    </div>
  );
}

