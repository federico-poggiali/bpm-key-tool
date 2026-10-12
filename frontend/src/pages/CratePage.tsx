import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode, type DragEvent, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type CrateOut, type CrateRecord, type CubeOut, type UnitOut, type UnsortedRecord } from "../api/api";
import { Cover } from "../components/Cover";
import { ShelfSelect } from "../components/ShelfSelect";
import { cubeName, placeLabel, placesOf, type Place } from "../crate";
import { pushToast } from "../toast";
import styles from "./CratePage.module.css";

const CELL_MIN = 64; // one cube on the wall, in px: sized to fit the wall into the page
const CELL_MAX = 132;
const MAX_X = 60;
const MAX_Y = 30;
const PRESETS = [
  { label: "1×1", rows: 1, cols: 1 },
  { label: "1×4", rows: 1, cols: 4 },
  { label: "2×2", rows: 2, cols: 2 },
  { label: "2×4", rows: 2, cols: 4 },
  { label: "4×4", rows: 4, cols: 4 },
  { label: "5×5", rows: 5, cols: 5 },
];
const DRAG_TYPE = "application/x-spincount-record";

type Mode = "dig" | "build";
type Selection = { kind: "cube" | "unit"; id: number } | null;
type Rect = { x: number; y: number; rows: number; cols: number };

const cubeCount = (cube: CubeOut) => cube.sections.reduce((n, s) => n + s.records.length, 0);

function overlaps(a: Rect, b: Rect) {
  return a.x < b.x + b.cols && b.x < a.x + a.cols && a.y < b.y + b.rows && b.y < a.y + a.rows;
}

/** The first free spot for a new unit, scanning the wall row by row. */
function freeSpot(units: UnitOut[], rows: number, cols: number) {
  for (let y = 0; y <= MAX_Y; y++)
    for (let x = 0; x <= MAX_X; x++)
      if (!units.some((u) => overlaps({ x, y, rows, cols }, u))) return { x, y };
  return { x: 0, y: MAX_Y };
}

const matches = (r: CrateRecord, q: string) => `${r.artist} ${r.title}`.toLowerCase().includes(q);

export default function CratePage() {
  const client = useQueryClient();
  const crate = useQuery({ queryKey: ["crate"], queryFn: api.getCrate });
  const [mode, setMode] = useState<Mode>("dig");
  const [selected, setSelected] = useState<Selection>(null);
  const [find, setFind] = useState("");

  const run = useMutation({
    mutationFn: (fn: () => Promise<CrateOut | void>) => fn(),
    onSuccess: (data) => (data ? client.setQueryData(["crate"], data) : client.invalidateQueries({ queryKey: ["crate"] })),
  });
  const act = (fn: () => Promise<CrateOut | void>) => run.mutate(fn);

  const units = crate.data?.units ?? [];
  const unsorted = crate.data?.unsorted ?? [];
  const places = useMemo(() => placesOf(units), [units]);

  const q = find.trim().toLowerCase();
  const found = useMemo(() => {
    if (!q) return [];
    return [...places.values()].flatMap((p) => p.section.records.filter((r) => matches(r, q)).map((record) => ({ record, place: p })));
  }, [places, q]);
  const hitSections = useMemo(() => new Set(found.map((f) => f.place.section.id)), [found]);

  const placeRecord = (recordId: number, sectionId: number | null) => act(() => api.place([recordId], sectionId));
  const cube = selected?.kind === "cube" ? units.flatMap((u) => u.cubes.map((c) => ({ unit: u, cube: c }))).find((x) => x.cube.id === selected.id) : undefined;
  const unit = selected?.kind === "unit" ? units.find((u) => u.id === selected.id) : undefined;

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <span className="micro">crate</span>
          <h1>Your shelf</h1>
        </div>
        <div className={styles.tools}>
          <label className={styles.find}>
            <span className="sr">Find a record on the shelf</span>
            <input className="field-input" type="search" placeholder="Where is…" value={find} onChange={(e) => setFind(e.target.value)} />
          </label>
          <div className={styles.modes} role="group" aria-label="Mode">
            {(["dig", "build"] as const).map((m) => (
              <button key={m} type="button" aria-pressed={mode === m} className={mode === m ? styles.on : ""} onClick={() => { setMode(m); setSelected(null); }}>
                {m === "dig" ? "Dig" : "Build"}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className={styles.layout}>
        <section className={styles.wallWrap} aria-label="Shelf">
          {crate.isPending ? (
            <p className={styles.hint}>Loading the shelf…</p>
          ) : units.length === 0 && mode === "dig" ? (
            <div className={styles.empty}>
              <h2>No shelf yet</h2>
              <p>Draw your shelving: add units of cubes, name each cube, then drag records into them.</p>
              <button className="primary" onClick={() => setMode("build")}>Build your shelf</button>
            </div>
          ) : (
            <Wall units={units} mode={mode} selected={selected} onSelect={setSelected} hits={q ? hitSections : null}
              onMove={(u, x, y) => act(() => api.patchUnit(u.id, { x, y }))} onDropRecord={placeRecord} />
          )}
          {mode === "build" && units.length > 0 && <p className={styles.hint}>Drag a unit by its name tag to move it. Click a cube to name it and add dividers.</p>}
        </section>

        <aside className={styles.panel} aria-label="Crate panel">
          {q && <FindResults found={found} unsortedHits={unsorted.filter((r) => matches(r, q))} onShow={(c) => setSelected({ kind: "cube", id: c.id })} />}
          {cube ? (
            <CubePanel key={cube.cube.id} unit={cube.unit} cube={cube.cube} places={places} act={act} onPlace={placeRecord} onClose={() => setSelected(null)} />
          ) : unit && mode === "build" ? (
            <UnitPanel key={unit.id} unit={unit} units={units} act={act} onClose={() => setSelected(null)} />
          ) : mode === "build" ? (
            <AddUnit units={units} act={act} />
          ) : (
            <Tray records={unsorted} places={places} onPlace={placeRecord} />
          )}
        </aside>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- wall */

function Wall({ units, mode, selected, onSelect, hits, onMove, onDropRecord }: {
  units: UnitOut[]; mode: Mode; selected: Selection; onSelect: (s: Selection) => void; hits: Set<number> | null;
  onMove: (u: UnitOut, x: number, y: number) => void; onDropRecord: (recordId: number, sectionId: number) => void;
}) {
  const [drag, setDrag] = useState<{ id: number; dx: number; dy: number } | null>(null);
  const [room, setRoom] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = box.current?.parentElement;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setRoom(entry.contentRect.width));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const extra = mode === "build" ? 2 : 0;
  const cols = Math.max(4, ...units.map((u) => u.x + u.cols)) + extra;
  const CELL = room ? Math.max(CELL_MIN, Math.min(CELL_MAX, Math.floor((room - 8) / cols))) : 112;
  const rows = Math.max(1, ...units.map((u) => u.y + u.rows)) + (mode === "build" ? 1 : 0);
  const moveTo = (u: UnitOut, x: number, y: number) => {
    x = Math.min(MAX_X, Math.max(0, x));
    y = Math.min(MAX_Y, Math.max(0, y));
    if (x === u.x && y === u.y) return;
    if (units.some((o) => o.id !== u.id && overlaps({ ...u, x, y }, o))) pushToast("That spot is taken by another unit.", "info");
    else onMove(u, x, y);
  };
  return (
    <div ref={box} className={`${styles.wall} ${mode === "build" ? styles.building : ""}`} style={{ width: cols * CELL, height: rows * CELL, "--cell": `${CELL}px` } as CSSProperties}>
      {units.map((u) => {
        const moving = drag?.id === u.id ? drag : null;
        const at = { ...u, x: Math.max(0, u.x + (moving?.dx ?? 0)), y: Math.max(0, u.y + (moving?.dy ?? 0)) };
        const blocked = !!moving && units.some((o) => o.id !== u.id && overlaps(at, o));
        return (
          <Unit key={u.id} cell={CELL} unit={u} at={at} mode={mode} selected={selected} onSelect={onSelect} hits={hits} blocked={blocked}
            onDrag={(dx, dy) => setDrag(dx === null ? null : { id: u.id, dx, dy: dy! })}
            onDrop={() => { setDrag(null); moveTo(u, at.x, at.y); }}
            onNudge={(dx, dy) => moveTo(u, u.x + dx, u.y + dy)}
            onDropRecord={onDropRecord} />
        );
      })}
    </div>
  );
}

function Unit({ cell: CELL, unit, at, mode, selected, onSelect, hits, blocked, onDrag, onDrop, onNudge, onDropRecord }: {
  cell: number; unit: UnitOut; at: Rect; mode: Mode; selected: Selection; onSelect: (s: Selection) => void; hits: Set<number> | null; blocked: boolean;
  onDrag: (dx: number | null, dy?: number) => void; onDrop: () => void; onNudge: (dx: number, dy: number) => void; onDropRecord: (recordId: number, sectionId: number) => void;
}) {
  const start = useRef<{ x: number; y: number; moved: boolean } | null>(null);
  const building = mode === "build";

  const down = (e: ReactPointerEvent<HTMLButtonElement>) => {
    if (!building) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    start.current = { x: e.clientX, y: e.clientY, moved: false };
  };
  const move = (e: ReactPointerEvent) => {
    if (!start.current) return;
    const dx = Math.round((e.clientX - start.current.x) / CELL);
    const dy = Math.round((e.clientY - start.current.y) / CELL);
    if (dx || dy) start.current.moved = true;
    onDrag(dx, dy);
  };
  const up = () => {
    if (!start.current) return;
    const moved = start.current.moved;
    start.current = null;
    if (moved) onDrop();
    else { onDrag(null); onSelect({ kind: "unit", id: unit.id }); }
  };
  const nudge = (e: ReactKeyboardEvent) => {
    if (!building) return;
    const step = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
    if (!step) return;
    e.preventDefault();
    onNudge(step[0], step[1]);
  };

  const isSelected = selected?.kind === "unit" && selected.id === unit.id;
  return (
    <div className={`${styles.unit} ${isSelected ? styles.selected : ""} ${blocked ? styles.blocked : ""}`} data-testid="unit"
      style={{ left: at.x * CELL, top: at.y * CELL, width: unit.cols * CELL, height: unit.rows * CELL, gridTemplateColumns: `repeat(${unit.cols}, 1fr)`, gridTemplateRows: `repeat(${unit.rows}, 1fr)` }}>
      {building ? (
        <button type="button" className={`${styles.tag} ${styles.handle}`} onPointerDown={down} onPointerMove={move} onPointerUp={up} onKeyDown={nudge}
          onClick={(e) => e.detail === 0 && onSelect({ kind: "unit", id: unit.id })} aria-label={`${unit.name}: drag or use arrow keys to move, Enter to edit`}>
          {unit.name}
        </button>
      ) : (
        <span className={styles.tag}>{unit.name}</span>
      )}
      {unit.cubes.map((c) => (
        <Cube key={c.id} cube={c} mode={mode} selected={selected?.kind === "cube" && selected.id === c.id} hits={hits}
          onSelect={() => onSelect({ kind: "cube", id: c.id })} onDropRecord={onDropRecord} />
      ))}
    </div>
  );
}

/** A deterministic spine height so the stack looks like real sleeves, not a bar chart. */
const spine = (id: number) => 74 + ((id * 37) % 23);

function Cube({ cube, mode, selected, hits, onSelect, onDropRecord }: {
  cube: CubeOut; mode: Mode; selected: boolean; hits: Set<number> | null; onSelect: () => void; onDropRecord: (recordId: number, sectionId: number) => void;
}) {
  const [over, setOver] = useState<number | null>(null);
  const count = cubeCount(cube);
  const hit = hits ? cube.sections.some((s) => hits.has(s.id)) : false;
  const accept = (e: DragEvent, sectionId: number) => {
    if (!e.dataTransfer.types.includes(DRAG_TYPE)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setOver(sectionId);
  };
  const drop = (e: DragEvent, sectionId: number) => {
    const id = Number(e.dataTransfer.getData(DRAG_TYPE));
    setOver(null);
    if (id) { e.preventDefault(); onDropRecord(id, sectionId); }
  };
  return (
    <div className={`${styles.cube} ${selected ? styles.selected : ""} ${hits ? (hit ? styles.hit : styles.dim) : ""}`} data-testid="cube">
      <button type="button" className={styles.cubeBtn} onClick={onSelect} aria-pressed={selected}
        aria-label={`${cubeName(cube)}, ${count} record${count === 1 ? "" : "s"}${mode === "build" ? ", edit" : ""}`}>
        <span className={styles.cubeName}>{cube.name || <i>unnamed</i>}</span>
        <span className={styles.cubeCount}>{count}</span>
      </button>
      <div className={styles.sections}>
        {cube.sections.map((s) => (
          <div key={s.id} className={`${styles.section} ${over === s.id ? styles.over : ""} ${hits?.has(s.id) ? styles.hit : ""}`}
            style={{ flexGrow: s.records.length + 2 }} onClick={onSelect}
            onDragOver={(e) => accept(e, s.id)} onDragLeave={() => setOver(null)} onDrop={(e) => drop(e, s.id)}
            title={`${s.name || "section " + (s.position + 1)}: ${s.records.length}`}>
            <div className={styles.spines} aria-hidden="true">
              {s.records.slice(0, 48).map((r) => (
                <i key={r.id} style={{ height: `${spine(r.id)}%` }} />
              ))}
            </div>
            {cube.sections.length > 1 && <span className={styles.sectionName}>{s.name || "·"}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- panel */

function RecordRow({ record, sectionId, places, onPlace, children }: {
  record: CrateRecord; sectionId: number | null; places: Map<number, Place>; onPlace: (recordId: number, sectionId: number | null) => void; children?: ReactNode;
}) {
  return (
    <li className={styles.row} draggable onDragStart={(e) => { e.dataTransfer.setData(DRAG_TYPE, String(record.id)); e.dataTransfer.effectAllowed = "move"; }}>
      <span className={styles.grip} aria-hidden="true">⋮⋮</span>
      <Cover url={record.cover_url} size={40} />
      <div className={styles.rowText}>
        <Link to={`/records/${record.id}`}><b>{record.title}</b></Link>
        <span>{record.artist}{record.year ? ` · ${record.year}` : ""}</span>
        {children}
      </div>
      <ShelfSelect className={styles.move} value={sectionId} places={places} label={`Move ${record.title}`} onChange={(id) => onPlace(record.id, id)} />
    </li>
  );
}

function Tray({ records, places, onPlace }: { records: UnsortedRecord[]; places: Map<number, Place>; onPlace: (recordId: number, sectionId: number | null) => void }) {
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

function FindResults({ found, unsortedHits, onShow }: { found: { record: CrateRecord; place: Place }[]; unsortedHits: CrateRecord[]; onShow: (c: CubeOut) => void }) {
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

/** A text field that saves when you leave it or press Enter. */
function Inline({ value, onSave, label, placeholder, multiline }: { value: string; onSave: (v: string) => void; label: string; placeholder?: string; multiline?: boolean }) {
  const [text, setText] = useState(value);
  const commit = () => text.trim() !== value && onSave(text.trim());
  const props = {
    className: "field-input", "aria-label": label, placeholder, value: text,
    onChange: (e: { target: { value: string } }) => setText(e.target.value), onBlur: commit,
  };
  return multiline ? <textarea {...props} rows={2} /> : <input {...props} onKeyDown={(e) => e.key === "Enter" && (e.currentTarget as HTMLInputElement).blur()} />;
}

function CubePanel({ unit, cube, places, act, onPlace, onClose }: {
  unit: UnitOut; cube: CubeOut; places: Map<number, Place>; act: (fn: () => Promise<CrateOut | void>) => void;
  onPlace: (recordId: number, sectionId: number | null) => void; onClose: () => void;
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

function AddUnit({ units, act }: { units: UnitOut[]; act: (fn: () => Promise<CrateOut | void>) => void }) {
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

function UnitPanel({ unit, units, act, onClose }: { unit: UnitOut; units: UnitOut[]; act: (fn: () => Promise<CrateOut | void>) => void; onClose: () => void }) {
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
