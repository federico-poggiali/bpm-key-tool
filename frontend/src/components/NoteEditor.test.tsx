import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NoteOut } from "../api/api";
import { NoteEditor } from "./NoteEditor";

const note: NoteOut = {
  id: 7, type: "prose", body: "huge energy", record_id: 1, track_id: null,
  created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
};

function setup(props: Partial<React.ComponentProps<typeof NoteEditor>> = {}) {
  const onSave = vi.fn();
  const onDelete = vi.fn();
  render(<NoteEditor note={note} target="Record"
    onSave={onSave} onDelete={onDelete} defaultEditing {...props} />);
  return { onSave, onDelete };
}

describe("NoteEditor", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("autosaves once, after typing stops, and says so", () => {
    const { onSave } = setup();
    const body = screen.getByLabelText("Note text");
    fireEvent.change(body, { target: { value: "huge energy, the floor erupted" } });
    act(() => { vi.advanceTimersByTime(300); });
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText("Saving…")).toBeInTheDocument();
    fireEvent.change(body, { target: { value: "huge energy, the floor erupted!" } });
    act(() => { vi.advanceTimersByTime(900); });
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith({ body: "huge energy, the floor erupted!" });
    expect(screen.getByText("Saved")).toBeInTheDocument();
  });

  it("does not save when nothing changed, or when changed back", () => {
    const { onSave } = setup();
    const body = screen.getByLabelText("Note text");
    fireEvent.change(body, { target: { value: "x" } });
    fireEvent.change(body, { target: { value: "huge energy" } });
    act(() => { vi.advanceTimersByTime(2000); });
    expect(onSave).not.toHaveBeenCalled();
  });

  it("flushes a pending edit immediately when you press Done", () => {
    const { onSave } = setup();
    fireEvent.change(screen.getByLabelText("Note text"), { target: { value: "quick" } });
    fireEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(onSave).toHaveBeenCalledWith({ body: "quick" });
  });

  it("asks for confirmation before deleting", () => {
    const { onDelete } = setup({ defaultEditing: false });
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("shows the note text and what it is about when not editing", () => {
    setup({ defaultEditing: false, target: "A1 One More Time" });
    expect(screen.getByText("huge energy")).toBeInTheDocument();
    expect(screen.getByText("A1 One More Time")).toBeInTheDocument();
  });
});
