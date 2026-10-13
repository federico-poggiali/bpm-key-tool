import { useEffect, useRef, useState, type CSSProperties, type DragEvent, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent } from "react";
import type { CubeOut, UnitOut } from "../../api/api";
import { cubeName } from "../../crate";
import { pushToast } from "../../toast";
import styles from "./crate.module.css";
import { cubeCount, DRAG_TYPE, MAX_X, MAX_Y, overlaps, type Mode, type Rect, type Selection } from "./common";

const CELL_MIN = 64; // one cube on the wall, in px: sized to fit the wall into the page
const CELL_MAX = 132;

export function Wall({ units, mode, selected, onSelect, hits, onMove, onDropRecord }: {
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
