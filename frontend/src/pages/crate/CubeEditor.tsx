import { api, type CubeOut, type UnitOut } from "../../api/api";
import { cubeName, type Place } from "../../crate";
import styles from "./crate.module.css";
import { Inline, RecordRow, type Act, type PlaceRecord } from "./common";

export function CubePanel({ unit, cube, places, act, onPlace, onClose }: {
  unit: UnitOut; cube: CubeOut; places: Map<number, Place>; act: Act;
  onPlace: PlaceRecord; onClose: () => void;
}) {
  const split = cube.sections.length > 1;
  return (
    <div className={styles.card}>
      <div className={styles.cardHead}>
        <div>
          <span className="micro">{unit.name} · row {cube.row + 1}, cube {cube.col + 1}</span>
          <h2>{cubeName(cube)}</h2>
        </div>
        <button type="button" className="ghost small" onClick={onClose}>Close</button>
      </div>
      <label className={styles.field}>
        <span className="micro">name / tag</span>
        <Inline key={`n${cube.name}`} value={cube.name} label="Cube name" placeholder="e.g. Jazz, House A–M, To sell" onSave={(name) => act(() => api.patchCube(cube.id, { name }))} />
      </label>
      <label className={styles.field}>
        <span className="micro">description</span>
        <Inline key={`d${cube.description}`} value={cube.description} label="Cube description" multiline placeholder="Styles or tags that belong here, used for suggestions" onSave={(description) => act(() => api.patchCube(cube.id, { description }))} />
      </label>

      {cube.sections.map((s, i) => (
        <div key={s.id} className={styles.sectionCard}>
          {split && (
            <div className={styles.sectionHead}>
              <Inline key={`s${s.name}`} value={s.name} label={`Section ${i + 1} name`} placeholder={`Section ${i + 1}, e.g. A–M`} onSave={(name) => act(() => api.renameSection(s.id, name))} />
              <button type="button" className="ghost small danger" onClick={() => act(() => api.deleteSection(s.id))}
                title={`Remove this divider; its records join section ${i === 0 ? 2 : i}`}>Remove</button>
            </div>
          )}
          {s.records.length === 0 ? (
            <p className={styles.hint}>Empty. Drag records here from Unsorted.</p>
          ) : (
            <ul className={styles.rows} aria-label={`Records in ${split ? s.name || `section ${i + 1}` : cubeName(cube)}`}>
              {s.records.map((r) => <RecordRow key={r.id} record={r} sectionId={s.id} places={places} onPlace={onPlace} />)}
            </ul>
          )}
        </div>
      ))}
      <button type="button" className="ghost" onClick={() => act(() => api.addSection(cube.id))}>+ Add divider</button>
    </div>
  );
}
