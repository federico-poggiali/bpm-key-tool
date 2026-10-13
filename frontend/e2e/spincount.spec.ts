import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const VAULT = path.resolve("e2e/.run/vault/Records");
const vaultFiles = () => (fs.existsSync(VAULT) ? fs.readdirSync(VAULT).filter((f) => f.endsWith(".md")) : []);

// Keys are off until switched on in Settings; these flows cover them, so switch them on.
test.beforeEach(async ({ page }, info) => {
  if (info.title.startsWith("settings: keys")) return;
  await page.addInitScript(() => localStorage.setItem("spincount.keys", "on"));
});

test("add a record, take a note, find it by search, and see it in the vault", async ({ page }) => {
  // 1. Add a record (Discogs is mocked server-side with real saved responses).
  await page.goto("/add");
  await page.getByLabel("Discogs link").fill("https://www.discogs.com/release/9261843");
  await page.getByRole("button", { name: "owned", exact: true }).click();
  await page.getByRole("button", { name: "Add record" }).click();
  await expect(page).toHaveURL(/\/records\/\d+/);
  await expect(page.getByRole("heading", { level: 1, name: "7_1 12-inch Mixes" })).toBeVisible();
  // Nothing runs by itself: choose to analyse the whole record, and watch its progress.
  await expect(page.getByTestId("job-analysis")).toHaveCount(0);
  await page.getByRole("button", { name: "Analyse whole record" }).click();
  await expect(page.getByTestId("job-analysis").getByRole("status")).toHaveText("done");
  // Results wait for validation before they are saved onto the tracks.
  await expect(page.getByText(/tracks? to validate/)).toBeVisible();
  await page.getByRole("button", { name: "Validate all" }).click();
  await expect(page.getByText(/tracks? to validate/)).toHaveCount(0);
  await page.getByRole("button", { name: "Add to Discogs collection" }).click();
  await expect(page.getByTestId("job-discogs-sync").getByRole("status")).toHaveText("done");
  await expect(page.getByRole("row", { name: /Ambivalent Remix/ })).toContainText("8A (current)");

  // 2. Adding it again opens the existing record and says so, not duplicated.
  await page.goto("/add");
  await page.getByLabel("Discogs link").fill("https://www.discogs.com/release/9261843");
  await page.getByRole("button", { name: "Add record" }).click();
  await expect(page.getByText("Already in your library.")).toBeVisible();

  // 3. Open it and write a prose note.
  await page.goto("/");
  await page.getByRole("link", { name: /7_1 12-inch Mixes/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "7_1 12-inch Mixes" })).toBeVisible();
  await page.getByRole("tab", { name: /Notes/ }).click();
  await page.getByPlaceholder("Huge energy").fill("Huge energy, the floor erupted at midnight.");
  await page.getByRole("button", { name: "Add note" }).click();
  await expect(page.getByText("Huge energy, the floor erupted at midnight.")).toBeVisible();


  // 5. "/" jumps to search; exact search finds the note and opens it highlighted.
  await page.locator("body").click({ position: { x: 700, y: 5 } });
  await page.keyboard.press("/");
  await expect(page).toHaveURL(/\/search/);
  await page.getByRole("button", { name: "Exact" }).click();
  await page.getByRole("searchbox").fill("erupted");
  const hit = page.getByRole("link", { name: /Huge energy/ });
  await expect(hit.locator("mark")).toHaveText("erupted");
  await hit.click();
  await expect(page.locator("[data-highlight='true']")).toContainText("floor erupted");

  // 6. The same note and the hand-set BPM end up in the generated Obsidian file.
  await expect
    .poll(() => {
      const file = vaultFiles().find((f) => f.includes("(9261843)"));
      return file ? fs.readFileSync(path.join(VAULT, file), "utf8") : "";
    })
    .toContain("Huge energy, the floor erupted at midnight.");
  const text = fs.readFileSync(path.join(VAULT, vaultFiles().find((f) => f.includes("(9261843)"))!), "utf8");
  expect(text).toContain("generated_by: vinyl-second-brain");
});

test("library filters live in the URL and the back button restores them", async ({ page, request }) => {
  await request.post("/api/records/intake", { data: { discogs_url: "https://www.discogs.com/release/46673", status: "owned" } });
  await page.goto("/");
  await expect(page.getByTestId("count")).toHaveText("2 records");

  // BPM and key belong to tracks, so their filters only exist in the tracks view.
  await expect(page.getByRole("button", { name: "9B, G major" })).toHaveCount(0);
  await page.getByRole("button", { name: "Tracks", exact: true }).click();
  await page.getByRole("button", { name: "Key", exact: true }).click();
  await page.getByRole("button", { name: "9B, G major" }).click();
  await expect(page).toHaveURL(/key=9B/);
  await page.goBack();
  await expect(page).not.toHaveURL(/key=/);
  await page.goBack();

  await page.getByRole("button", { name: "Grid" }).click();
  await expect(page).toHaveURL(/view=grid/);
  await page.goBack();
  await expect(page).not.toHaveURL(/view=grid/);
  await expect(page.getByTestId("count")).toHaveText("2 records");

  // Styles come from Discogs: 46673 is UK Garage + Techno, 9261843 is Acid + Techno.
  await page.getByRole("button", { name: "Styles", exact: true }).hover();
  await page.getByRole("button", { name: /UK Garage/ }).click();
  await expect(page).toHaveURL(/style=UK\+Garage/);
  await expect(page.getByTestId("count")).toHaveText("1 records");
  await page.goBack();
  await expect(page).not.toHaveURL(/style=/);
  await expect(page.getByTestId("count")).toHaveText("2 records");

  await page.goto("/?key=9B&view=tracks");
  await expect(page.getByTestId("count")).toHaveText("1 tracks");
  await page.getByRole("button", { name: "Key", exact: true }).click();
  await expect(page.getByRole("button", { name: "9B, G major" })).toHaveAttribute("aria-pressed", "true");
});

test("settings: keys are hidden until switched on", async ({ page }) => {
  await page.goto("/?view=tracks");
  await expect(page.getByRole("button", { name: "Key", exact: true })).toHaveCount(0);
  await page.goto("/settings");
  await page.getByLabel("Analyse and show musical key").check();
  await page.goto("/?view=tracks");
  await expect(page.getByRole("button", { name: "Key", exact: true })).toBeVisible();
});

test("settings: sync the vault and see the result", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByTestId("vault-dir")).toContainText("e2e/.run/vault");
  await page.getByRole("button", { name: "Sync vault now" }).click();
  await expect(page.getByTestId("last-result")).toContainText("unchanged");
});

test("a record's styles can be edited, survive a reload, and be reset to Discogs", async ({ page, request }) => {
  const records = await (await request.get("/api/records")).json();
  const id = records.items.find((r: { discogs_release_id: number }) => r.discogs_release_id === 46673).id;
  await page.goto(`/records/${id}`);
  await expect(page.getByRole("list", { name: "Styles" })).toContainText("UK Garage");
  await expect(page.getByTestId("styles-edited")).toHaveCount(0);

  await page.getByRole("button", { name: "Remove style UK Garage" }).click();
  await page.getByLabel("Add a style").fill("Breakbeat");
  await page.getByLabel("Add a style").press("Enter");
  await expect(page.getByTestId("styles-edited")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("list", { name: "Styles" })).toContainText("Breakbeat");
  await expect(page.getByRole("list", { name: "Styles" })).not.toContainText("UK Garage");

  await page.getByRole("button", { name: "Reset to Discogs" }).click();
  await expect(page.getByRole("list", { name: "Styles" })).toContainText("UK Garage");
  await expect(page.getByTestId("styles-edited")).toHaveCount(0);
});

test("make a label: preview follows the edits, the record stays untouched, and it downloads as a 62 mm PNG", async ({ page, request }) => {
  const records = await (await request.get("/api/records")).json();
  const id = records.items.find((r: { discogs_release_id: number }) => r.discogs_release_id === 9261843).id;
  await page.goto(`/records/${id}`);
  await page.getByRole("link", { name: "Make label" }).click();
  await expect(page).toHaveURL(new RegExp(`/records/${id}/label$`));

  const main = page.getByRole("img", { name: "Main label preview" });
  await expect(main).toBeVisible();
  await expect(page.getByRole("img", { name: "Tracks label preview" })).toBeVisible();
  const before = await main.getAttribute("src");

  await page.getByLabel("Country", { exact: true }).fill("UK");
  await expect.poll(() => main.getAttribute("src")).not.toBe(before);
  const withCountry = await main.getAttribute("src");
  await page.getByLabel("Print country").uncheck();
  await expect.poll(() => main.getAttribute("src")).not.toBe(withCountry);

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download", exact: true }).first().click();
  const file = await download.then(async (d) => ({ name: d.suggestedFilename(), path: await d.path() }));
  expect(file.name).toMatch(/\(main\)\.png$/);
  const png = fs.readFileSync(file.path);
  expect([png.readUInt32BE(16), png.readUInt32BE(20), png[24], png[25]]).toEqual([696, 472, 1, 0]); // 1-bit greyscale

  // Edits are for this print only.
  const record = await (await request.get(`/api/records/${id}`)).json();
  expect(record.title).toBe("7_1 12-inch Mixes");

  await page.goto("/records/99999/label");
  await expect(page.getByRole("heading", { name: /isn't in your library/ })).toBeVisible();
});

test("make a label for a record that is not in the library: blank, and from a pasted link", async ({ page, request }) => {
  const before = (await (await request.get("/api/records")).json()).total;
  await page.goto("/labels");
  await page.getByRole("button", { name: "Start blank" }).click();
  await page.getByLabel("Artist", { exact: true }).fill("Test Artist");
  await page.getByLabel("Title", { exact: true }).fill("Test Title");
  await expect(page.getByRole("img", { name: "Main label preview" })).toBeVisible();
  await page.getByRole("button", { name: "Add track" }).click();
  await expect(page.getByRole("img", { name: "Tracks label preview" })).toBeVisible();

  await page.getByLabel("Discogs link").fill("https://www.discogs.com/release/46673");
  await page.getByRole("button", { name: "Fetch details" }).click();
  await expect(page.getByLabel("Title", { exact: true })).not.toHaveValue("Test Title");
  await expect(page.getByRole("img", { name: "Main label preview" })).toBeVisible();
  expect((await (await request.get("/api/records")).json()).total).toBe(before);
});

test("crate: draw a shelf, name a cube, file a record by its suggestion, and find it again", async ({ page, request }) => {
  await request.post("/api/records/intake", { data: { discogs_url: "https://www.discogs.com/release/9261843", status: "owned" } });

  await page.goto("/");
  await page.getByRole("navigation", { name: "Library" }).getByRole("link", { name: "Crate" }).click();
  await expect(page).toHaveURL(/\/crate$/);

  // Build: a 1x4 unit, then name its first cube after a style.
  await page.getByRole("group", { name: "Mode" }).getByRole("button", { name: "Build" }).click();
  await page.getByRole("textbox", { name: "name" }).fill("Kallax E2E");
  await page.getByRole("button", { name: "1×4" }).click();
  await page.getByRole("button", { name: "Add unit" }).click();
  const unit = page.getByTestId("unit").filter({ hasText: "Kallax E2E" });
  await expect(unit.getByTestId("cube")).toHaveCount(4);
  await unit.getByTestId("cube").first().getByRole("button").first().click();
  await page.getByLabel("Cube name").fill("Acid");
  await page.getByLabel("Cube name").press("Enter");
  await expect(page.getByRole("heading", { level: 2, name: "Acid" })).toBeVisible();
  await page.getByRole("button", { name: "+ Add divider" }).click();
  await page.getByLabel("Section 2 name").fill("T–Z");
  await page.getByLabel("Section 2 name").press("Enter");

  // Dig: the unsorted record is suggested for that cube; one click files it.
  await page.getByRole("group", { name: "Mode" }).getByRole("button", { name: "Dig" }).click();
  const tray = page.getByRole("list", { name: "Unsorted records" });
  const row = tray.getByRole("listitem").filter({ hasText: "7_1 12-inch Mixes" });
  await expect(row.getByRole("button", { name: /Kallax E2E › Acid › T–Z/ })).toBeVisible(); // style + artist initial
  await row.getByRole("button", { name: /Kallax E2E › Acid/ }).click();
  await expect(tray.getByRole("listitem").filter({ hasText: "7_1 12-inch Mixes" })).toHaveCount(0);

  // Where is it? Search shows the place, survives a reload.
  await page.reload();
  await page.getByRole("searchbox", { name: "Find a record on the shelf" }).fill("7_1");
  await expect(page.getByRole("status").filter({ hasText: "Found" })).toContainText("Kallax E2E › Acid › T–Z");
});

test("crate: adding a record to the library asks where it goes on the shelf", async ({ page, request }) => {
  const shelf = await (await request.post("/api/crate/units", { data: { name: "Garage shelf", rows: 1, cols: 2, x: 0, y: 3 } })).json();
  const cube = shelf.units.find((u: { name: string }) => u.name === "Garage shelf").cubes[1];
  await request.patch(`/api/crate/cubes/${cube.id}`, { data: { name: "UK Garage" } });

  await page.goto("/add");
  await page.getByLabel("Discogs link").fill("https://www.discogs.com/release/46673");
  await page.getByRole("button", { name: "owned", exact: true }).click();
  await page.getByRole("button", { name: "Add record" }).click();
  const prompt = page.getByRole("region", { name: "Where does it go?" });
  await expect(prompt).toContainText("Garage shelf › UK Garage"); // suggested from its UK Garage style
  await prompt.getByRole("button", { name: "Put it here" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Filed in" })).toContainText("Garage shelf › UK Garage");

  // Once placed, it is not asked again.
  await page.goto("/add");
  await page.getByLabel("Discogs link").fill("https://www.discogs.com/release/46673");
  await page.getByRole("button", { name: "owned", exact: true }).click();
  await page.getByRole("button", { name: "Add record" }).click();
  await expect(page.getByText("Already in your library.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Where does it go?" })).toHaveCount(0);
});

test("design tags in the Tag Manager, then put one on a record", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Tag Manager" }).click();
  await expect(page.getByRole("heading", { level: 2, name: "Energy" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Atmosphere" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Set role" })).toBeVisible();

  await page.getByLabel("New tag in Set role").fill("closer");
  await page.getByLabel("New tag in Set role").press("Enter");
  await expect(page.getByRole("region", { name: "Set role" }).getByRole("button", { name: "closer", exact: true })).toBeVisible();

  await page.getByLabel("New group name").fill("Occasion");
  await page.getByLabel("New group name").press("Enter");
  await expect(page.getByRole("region", { name: "Occasion" })).toBeVisible();

  await page.goto("/");
  await page.getByRole("link", { name: /7_1 12-inch Mixes/ }).first().click();
  await page.getByLabel("Add a tag to this record").selectOption("closer");
  await expect(page.getByRole("list", { name: "this record tags" })).toContainText("closer");
});
