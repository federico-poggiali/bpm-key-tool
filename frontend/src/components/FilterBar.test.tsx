import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Filters } from "../libraryParams";
import { FilterBar } from "./FilterBar";

const base: Filters = { q: "", tags: [], status: "owned", view: "grid", page: 1 };
const tags = [
  { name: "house", record_count: 3, track_count: 1 },
  { name: "peak", record_count: 0, track_count: 2 },
];

function setup(filters: Partial<Filters> = {}, onChange = vi.fn(), onClear = vi.fn()) {
  render(
    <FilterBar filters={{ ...base, ...filters }} defaultStatus="owned" tags={tags} keyFormat="camelot"
      onKeyFormat={vi.fn()} onChange={onChange} onClear={onClear} />,
  );
  return { onChange, onClear };
}

describe("FilterBar", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("debounces the text search into one change", async () => {
    const { onChange } = setup();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    await user.type(screen.getByRole("searchbox"), "daft");
    expect(onChange).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(350); });
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ q: "daft" });
  });

  it("turns the two BPM handles into bpmMin / bpmMax, and the ends into 'no limit'", () => {
    const { onChange } = setup();
    fireEvent.change(screen.getByLabelText("Minimum BPM"), { target: { value: "120" } });
    fireEvent.change(screen.getByLabelText("Maximum BPM"), { target: { value: "128" } });
    act(() => { vi.advanceTimersByTime(300); });
    expect(onChange).toHaveBeenLastCalledWith({ bpmMin: 120, bpmMax: 128 });
    fireEvent.change(screen.getByLabelText("Minimum BPM"), { target: { value: "60" } });
    act(() => { vi.advanceTimersByTime(300); });
    expect(onChange).toHaveBeenLastCalledWith({ bpmMin: undefined, bpmMax: 128 });
  });

  it("never lets the minimum pass the maximum", () => {
    const { onChange } = setup({ bpmMin: 100, bpmMax: 110 });
    fireEvent.change(screen.getByLabelText("Minimum BPM"), { target: { value: "150" } });
    act(() => { vi.advanceTimersByTime(300); });
    expect(onChange).toHaveBeenLastCalledWith({ bpmMin: 110, bpmMax: 110 });
  });

  it("picks a key, and clicking it again clears it", () => {
    const { onChange } = setup();
    fireEvent.click(screen.getByRole("button", { name: "8A, A minor" }));
    expect(onChange).toHaveBeenLastCalledWith({ key: "8A" });
  });

  it("shows the selected key as pressed and toggles it off", () => {
    const { onChange } = setup({ key: "8A" });
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

  it("switches views and status", () => {
    const { onChange } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Tracks" }));
    expect(onChange).toHaveBeenLastCalledWith({ view: "tracks" });
    fireEvent.change(screen.getByLabelText("status"), { target: { value: "wantlist" } });
    expect(onChange).toHaveBeenLastCalledWith({ status: "wantlist" });
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
