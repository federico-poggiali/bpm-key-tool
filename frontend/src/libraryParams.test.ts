import { describe, expect, it } from "vitest";
import { isFiltered, parseFilters, serializeFilters } from "./libraryParams";

describe("library URL state", () => {
  it("round-trips every filter through the query string", () => {
    const url = "q=daft&bpm_min=120&bpm_max=128&key=8A&tag=house&tag=peak&style=Deep+House&style=Techno&status=wantlist&view=tracks&page=3";
    const filters = parseFilters(new URLSearchParams(url), "owned");
    expect(filters).toEqual({ q: "daft", bpmMin: 120, bpmMax: 128, key: "8A", tags: ["house", "peak"], styles: ["Deep House", "Techno"], status: "wantlist", view: "tracks", page: 3 });
    expect(serializeFilters(filters, "owned").toString()).toBe(new URLSearchParams(url).toString());
  });

  it("keeps the URL clean for the default view", () => {
    const filters = parseFilters(new URLSearchParams(""), "owned");
    expect(filters).toMatchObject({ status: "owned", view: "grid", page: 1, tags: [], styles: [] });
    expect(serializeFilters(filters, "owned").toString()).toBe("");
    expect(isFiltered(filters, "owned")).toBe(false);
  });

  it("counts a style as an active filter", () => {
    expect(isFiltered(parseFilters(new URLSearchParams("style=Techno"), "owned"), "owned")).toBe(true);
  });

  it("uses the page's own default status, and 'all' removes the status filter", () => {
    expect(parseFilters(new URLSearchParams(""), "wantlist").status).toBe("wantlist");
    expect(parseFilters(new URLSearchParams("status=all"), "owned").status).toBe("all");
    expect(isFiltered(parseFilters(new URLSearchParams("status=all"), "owned"), "owned")).toBe(true);
  });

  it("ignores junk values instead of crashing", () => {
    const f = parseFilters(new URLSearchParams("bpm_min=abc&page=-4&view=nope&status=zzz"), "owned");
    expect(f).toMatchObject({ bpmMin: undefined, page: 1, view: "grid", status: "owned" });
  });
});
