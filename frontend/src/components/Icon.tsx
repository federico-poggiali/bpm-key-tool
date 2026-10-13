/** 16px line icons, 1.5px stroke, monochrome: they take the text colour of whatever holds them. */
const PATHS = {
  library: "M3 3.5h2.5v9H3zM7 3.5h2.5v9H7zM11.2 4l2.3-.6 2 8.6-2.3.6z",
  wishlist: "M8 13.5S2.5 10.3 2.5 6.4A2.9 2.9 0 0 1 8 5a2.9 2.9 0 0 1 5.5 1.4C13.5 10.3 8 13.5 8 13.5z",
  crate: "M2.5 2.5h11v11h-11zM2.5 8h11M8 2.5v11",
  add: "M8 3v10M3 8h10",
  label: "M2.5 4.5h11v7h-11zM5 7h4M5 9h6",
  tag: "M2.5 2.5h5l6 6-5 5-6-6zM5.25 5.25h.01",
  settings: "M8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4",
  search: "M7 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM10.6 10.6 14 14",
  table: "M2.5 3h11v10h-11zM2.5 6.5h11M2.5 10h11M6 3v10",
  grid: "M2.5 2.5h4.5v4.5h-4.5zM9 2.5h4.5v4.5H9zM2.5 9h4.5v4.5h-4.5zM9 9h4.5v4.5H9z",
  chevron: "M6 4l4 4-4 4",
  down: "M4 6l4 4 4-4",
  external: "M6 3H3v10h10v-3M9 2.5h4.5V7M13.5 2.5 7.5 8.5",
  close: "M4 4l8 8M12 4l-8 8",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 16 }: { name: IconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d={PATHS[name]} />
    </svg>
  );
}
