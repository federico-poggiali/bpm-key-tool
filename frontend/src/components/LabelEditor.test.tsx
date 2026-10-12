import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import type { LabelData } from "../api/api";
import { LabelEditor, parseList } from "./LabelEditor";

const label: LabelData = {
  artist: "Jeff Mills", title: "The Bells", label: "Axis", catno: "AX-1", year: "1994", country: null,
  styles: ["Techno"], note: "A short note.", qr_url: "https://www.discogs.com/release/1", hidden: [],
  tracks: [
    { position: "A1", bpm: "135", key: "4A", tags: ["peak"], note: null, skip: false, hidden: [] },
    { position: "B1", bpm: null, key: null, tags: [], note: null, skip: false, hidden: [] },
  ],
};

function setup(value: LabelData = label) {
  const onChange = vi.fn();
  render(<LabelEditor value={value} onChange={onChange} />);
  return onChange;
}
const lastCall = (fn: ReturnType<typeof vi.fn>) => fn.mock.calls.at(-1)![0] as LabelData;

describe("LabelEditor", () => {
  it("edits a printed value", () => {
    const onChange = setup();
    fireEvent.change(screen.getByLabelText("Artist"), { target: { value: "Someone Else" } });
    expect(lastCall(onChange).artist).toBe("Someone Else");
  });

  it("lets you type a value the database does not have, and clears it back to nothing", () => {
    const onChange = setup();
    fireEvent.change(screen.getByLabelText("Country"), { target: { value: "UK" } });
    expect(lastCall(onChange).country).toBe("UK");
    fireEvent.change(screen.getByLabelText("Year"), { target: { value: "" } });
    expect(lastCall(onChange).year).toBeNull();
  });

  it("hides and shows a field with its print tick", () => {
    const onChange = setup();
    fireEvent.click(screen.getByLabelText("Print label"));
    expect(lastCall(onChange).hidden).toEqual(["label"]);
    onChange.mockClear();
    render(<LabelEditor value={{ ...label, hidden: ["label", "year"] }} onChange={onChange} />);
    fireEvent.click(screen.getAllByLabelText("Print year")[1]);
    expect(lastCall(onChange).hidden).toEqual(["label"]);
  });

  it("hides a track field and skips a track", () => {
    const onChange = setup();
    fireEvent.click(screen.getByLabelText("Print bpm a1"));
    expect(lastCall(onChange).tracks![0].hidden).toEqual(["bpm"]);
    fireEvent.click(screen.getByLabelText("Include track B1"));
    expect(lastCall(onChange).tracks![1].skip).toBe(true);
    expect(lastCall(onChange).tracks![0].skip).toBe(false);
  });

  it("edits one track's values without touching the others", () => {
    const onChange = setup();
    fireEvent.change(screen.getByLabelText("BPM B1"), { target: { value: "128" } });
    const tracks = lastCall(onChange).tracks!;
    expect(tracks[1].bpm).toBe("128");
    expect(tracks[0].bpm).toBe("135");
  });

  it("keeps a trailing comma while typing a list", () => {
    function Harness() {
      const [value, setValue] = useState(label);
      return <LabelEditor value={value} onChange={setValue} />;
    }
    render(<Harness />);
    const input = screen.getByLabelText("Styles") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Techno, " } });
    expect(input.value).toBe("Techno, ");
    fireEvent.change(input, { target: { value: "Techno, Dub Techno" } });
    expect(input.value).toBe("Techno, Dub Techno");
  });

  it("splits a list on commas and drops blanks", () => {
    expect(parseList(" a, ,b ,, c")).toEqual(["a", "b", "c"]);
  });

  it("offers a QR toggle only when there is a link to encode", () => {
    setup({ ...label, qr_url: null });
    expect(screen.queryByLabelText("Print qr code")).toBeNull();
  });
});
