import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StyleEditor } from "./StyleEditor";

function setup(props: Partial<React.ComponentProps<typeof StyleEditor>> = {}) {
  const onChange = vi.fn();
  const onReset = vi.fn();
  render(<StyleEditor styles={["Deep House"]} suggestions={["Techno"]} manual={false} onChange={onChange} onReset={onReset} {...props} />);
  return { onChange, onReset };
}

describe("StyleEditor", () => {
  it("adds a style on Enter, trimmed", () => {
    const { onChange } = setup();
    const input = screen.getByLabelText("Add a style");
    fireEvent.change(input, { target: { value: "  Dub   Techno " } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(["Deep House", "Dub Techno"]);
  });

  it("ignores a style already there, whatever its case", () => {
    const { onChange } = setup();
    const input = screen.getByLabelText("Add a style");
    fireEvent.change(input, { target: { value: "deep house" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("removes a style", () => {
    const { onChange } = setup({ styles: ["Deep House", "Techno"] });
    fireEvent.click(screen.getByRole("button", { name: "Remove style Deep House" }));
    expect(onChange).toHaveBeenCalledWith(["Techno"]);
  });

  it("marks edited styles and offers a reset only then", () => {
    const { onReset } = setup({ manual: true });
    expect(screen.getByTestId("styles-edited")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reset to Discogs" }));
    expect(onReset).toHaveBeenCalled();
  });

  it("has no reset when the styles are Discogs' own", () => {
    setup();
    expect(screen.queryByRole("button", { name: "Reset to Discogs" })).toBeNull();
    expect(screen.queryByTestId("styles-edited")).toBeNull();
  });
});
