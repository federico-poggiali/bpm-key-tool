import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type CrateOut } from "../api/api";
import { placesOf } from "../crate";
import styles from "./crate/crate.module.css";
import { AddUnit, UnitPanel } from "./crate/BuildView";
import { matches, type Mode, type Selection } from "./crate/common";
import { CubePanel } from "./crate/CubeEditor";
import { FindResults, Tray } from "./crate/DigView";
import { Wall } from "./crate/Wall";

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
