import type { Status } from "./api/api";

export type View = "grid" | "table" | "tracks";
export const BPM_MIN = 60;
export const BPM_MAX = 200;

export type Filters = {
  q: string;
  bpmMin?: number;
  bpmMax?: number;
  key?: string; // Camelot code
  tags: string[];
  styles: string[]; // Discogs styles; the URL parameter is "style"
  status: Status | "all";
  view: View;
  page: number;
};

const num = (v: string | null) => {
  const n = v == null || v === "" ? NaN : Number(v);
  return Number.isFinite(n) ? n : undefined;
};

/** The URL is the single source of truth (records default to the table view) for the library view, so it survives refresh and is shareable. */
export function parseFilters(params: URLSearchParams, defaultStatus: Status): Filters {
  const status = params.get("status");
  const view = params.get("view");
  return {
    q: params.get("q") ?? "",
    bpmMin: num(params.get("bpm_min")),
    bpmMax: num(params.get("bpm_max")),
    key: params.get("key") ?? undefined,
    tags: params.getAll("tag"),
    styles: params.getAll("style"),
    status: status === "all" || status === "owned" || status === "wantlist" || status === "considering" ? status : defaultStatus,
    view: view === "grid" || view === "tracks" ? view : "table",
    page: Math.max(1, num(params.get("page")) ?? 1),
  };
}

export function serializeFilters(f: Filters, defaultStatus: Status): URLSearchParams {
  const p = new URLSearchParams();
  if (f.q) p.set("q", f.q);
  if (f.bpmMin != null) p.set("bpm_min", String(f.bpmMin));
  if (f.bpmMax != null) p.set("bpm_max", String(f.bpmMax));
  if (f.key) p.set("key", f.key);
  f.tags.forEach((t) => p.append("tag", t));
  f.styles.forEach((s) => p.append("style", s));
  if (f.status !== defaultStatus) p.set("status", f.status);
  if (f.view !== "table") p.set("view", f.view);
  if (f.page > 1) p.set("page", String(f.page));
  return p;
}

export const isFiltered = (f: Filters, defaultStatus: Status) =>
  !!(f.q || (f.view === "tracks" && (f.bpmMin != null || f.bpmMax != null || f.key)) || f.tags.length || f.styles.length || f.status !== defaultStatus);

export const pageSize = (view: View) => (view === "grid" ? 24 : 50);
