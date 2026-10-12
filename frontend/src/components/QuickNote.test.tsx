import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QuickNote } from "./QuickNote";

const create = vi.fn().mockResolvedValue({ id: 9 });
const patch = vi.fn().mockResolvedValue({});
const remove = vi.fn().mockResolvedValue({});
let notes: { id: number; body: string }[] = [];

vi.mock("../hooks", () => ({
  useRecord: () => ({ data: { notes }, isLoading: false }),
  useNoteMutations: () => ({ create: { mutateAsync: create }, patch: { mutateAsync: patch }, remove: { mutateAsync: remove } }),
}));

beforeEach(() => { vi.useFakeTimers(); create.mockClear(); patch.mockClear(); remove.mockClear(); notes = []; });

const open = () => fireEvent.click(screen.getByRole("button", { name: /note for Dub Plate/ }));
const type = (value: string) => { fireEvent.change(screen.getByLabelText("Note"), { target: { value } }); act(() => { vi.advanceTimersByTime(900); }); };

describe("QuickNote", () => {
  it("opens a blank pad and saves what you write as a prose note on the record", async () => {
    render(<QuickNote recordId={3} title="Dub Plate" filled={false} />);
    open();
    expect(screen.getByLabelText("Note")).toHaveValue("");
    type("Shelf B. Floor went off.");
    await act(async () => { await Promise.resolve(); });
    expect(create).toHaveBeenCalledWith({ type: "prose", body: "Shelf B. Floor went off.", record_id: 3, track_id: null });
  });

  it("edits the existing note and removes it when emptied", async () => {
    notes = [{ id: 5, body: "old" }];
    render(<QuickNote recordId={3} title="Dub Plate" filled />);
    open();
    expect(screen.getByLabelText("Note")).toHaveValue("old");
    type("new");
    await act(async () => { await Promise.resolve(); });
    expect(patch).toHaveBeenCalledWith({ id: 5, body: { body: "new" } });
    type("");
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(remove).toHaveBeenCalledWith(5);
  });
});
