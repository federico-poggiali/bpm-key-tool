import type { CubeOut, SectionOut, UnitOut } from "./api/api";

/** Where a section sits on the shelf. */
export type Place = { unit: UnitOut; cube: CubeOut; section: SectionOut };

export const cubeName = (cube: CubeOut) => cube.name || `Row ${cube.row + 1}, cube ${cube.col + 1}`;

/** "Kallax A › Jazz › A–M": the section is left out while a cube has no dividers. */
export function placeLabel(place: Place) {
  const parts = [place.unit.name, cubeName(place.cube)];
  if (place.cube.sections.length > 1) parts.push(place.section.name || `section ${place.section.position + 1}`);
  return parts.join(" › ");
}

/** Every section on the shelf by id, in shelf order. */
export function placesOf(units: UnitOut[]) {
  const map = new Map<number, Place>();
  for (const unit of units) for (const cube of unit.cubes) for (const section of cube.sections) map.set(section.id, { unit, cube, section });
  return map;
}
