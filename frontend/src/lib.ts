/** Camelot wheel: number 1-12, A = minor, B = major. Names match the backend's key labels. */
const MINOR = ["G# minor", "D# minor", "A# minor", "F minor", "C minor", "G minor", "D minor", "A minor", "E minor", "B minor", "F# minor", "C# minor"];
const MAJOR = ["B major", "F# major", "C# major", "G# major", "D# major", "A# major", "F major", "C major", "G major", "D major", "A major", "E major"];

export type WheelKey = { camelot: string; name: string; short: string };

export const WHEEL_KEYS: WheelKey[] = [
  ...MINOR.map((name, i) => ({ camelot: `${i + 1}A`, name, short: `${name.split(" ")[0]}m` })),
  ...MAJOR.map((name, i) => ({ camelot: `${i + 1}B`, name, short: name.split(" ")[0] })),
];

export const keyByCamelot = (camelot: string | null | undefined) =>
  WHEEL_KEYS.find((k) => k.camelot === camelot);

export type KeyFormat = "camelot" | "musical";

export function keyLabel(camelot: string | null | undefined, format: KeyFormat): string {
  const key = keyByCamelot(camelot);
  if (!key) return "";
  return format === "camelot" ? key.camelot : key.short;
}

export const formatBpm = (bpm: number | null | undefined) => (bpm == null ? "" : String(Math.round(bpm * 10) / 10));

export function altBpm(raw: Record<string, unknown> | null | undefined): number | null {
  const value = raw?.bpm_alt;
  return typeof value === "number" ? value : null;
}

export const LOW_CONFIDENCE = 0.4;

export function formatDuration(sec: number | null | undefined): string {
  if (sec == null) return "";
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}

export const STATUSES = ["owned", "wantlist", "considering"] as const;
