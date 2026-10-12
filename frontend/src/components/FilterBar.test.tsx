import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Filters } from "../libraryParams";
import { FilterBar } from "./FilterBar";

const base: Filters = { q: "", tags: [], styles: [], status: "owned", view: "grid", page: 1 };
const styleCounts = [
  { name: "Deep House", record_count: 4 },
  { name: "Techno", record_count: 2 },
];
const tags = [
  { name: "house", group: "Atmosphere", record_count: 3, track_count: 1 },
  { name: "peak", group: "Energy", record_count: 0, track_count: 2 },
];

function setup(filters: Partial<Filters> = {}, onChange = vi.fn(), onClear = vi.fn()) {
  render(
    <FilterBar filters={{ ...base, ...filters }} defaultStatus="owned" tags={tags} styleCounts={styleCounts} keyFormat="camelot"
      onKeyFormat={vi.fn()} onChange={onChange} onClear={onClear} onOpenSearch={vi.fn()} />,
  );
  return { onChange, onClear };
}

describe("FilterBar", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("opens the search popup when the search bar is clicked", async () => {
    const onOpenSearch = vi.fn();
    render(<FilterBar filters={base} defaultStatus="owned" tags={tags} styleCounts={styleCounts} keyFormat="camelot"
      onKeyFormat={vi.fn()} onChange={vi.fn()} onClear={vi.fn()} onOpenSearch={onOpenSearch} />);
    fireEvent.click(screen.getByRole("searchbox"));
    expect(onOpenSearch).toHaveBeenCalled();
  });

  it("hides BPM and key filters outside the tracks view, since they belong to tracks", () => {
    setup({ view: "grid" });
    expect(screen.queryByRole("button", { name: "8A, A minor" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Key" })).toBeNull();
  });

  it("picks a key, and clicking it again clears it", () => {
    const { onChange } = setup({ view: "tracks" });
    fireEvent.click(screen.getByRole("button", { name: "8A, A minor" }));
    expect(onChange).toHaveBeenLastCalledWith({ key: "8A" });
  });

  it("shows the selected key as pressed and toggles it off", () => {
    const { onChange } = setup({ view: "tracks", key: "8A" });
    const key = screen.getByRole("button", { name: "8A, A minor" });
    expect(key).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(key);
    expect(onChange).toHaveBeenLastCalledWith({ key: undefined });
  });

  it("toggles tags on and off, showing counts", () => {
    const { onChange } = setup({ tags: ["house"] });
    expect(screen.getByRole("button", { name: /house/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /peak/ })).toHaveTextContent("2");
    fireEvent.click(screen.getByRole("button", { name: /peak/ }));
    expect(onChange).toHaveBeenLastCalledWith({ tags: ["house", "peak"] });
    fireEvent.click(screen.getByRole("button", { name: /house/ }));
    expect(onChange).toHaveBeenLastCalledWith({ tags: [] });
  });

  it("toggles styles on and off, case-insensitively, showing record counts", () => {
    const { onChange } = setup({ styles: ["deep house"] });
    expect(screen.getByRole("button", { name: /Deep House/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Techno/ })).toHaveTextContent("2");
    fireEvent.click(screen.getByRole("button", { name: /Techno/ }));
    expect(onChange).toHaveBeenLastCalledWith({ styles: ["deep house", "Techno"] });
    fireEvent.click(screen.getByRole("button", { name: /Deep House/ }));
    expect(onChange).toHaveBeenLastCalledWith({ styles: [] });
  });

  it("switches views", () => {
    const { onChange } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Tracks" }));
    expect(onChange).toHaveBeenLastCalledWith({ view: "tracks" });
  });

  it("offers Clear only when something is filtered", () => {
    const { onClear } = setup({ q: "x" });
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onClear).toHaveBeenCalled();
  });

  it("has no Clear button on the untouched default view", () => {
    setup();
    expect(screen.queryByRole("button", { name: "Clear filters" })).toBeNull();
  });
});
