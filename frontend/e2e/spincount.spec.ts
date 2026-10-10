import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const VAULT = path.resolve("e2e/.run/vault/Records");
const vaultFiles = () => (fs.existsSync(VAULT) ? fs.readdirSync(VAULT).filter((f) => f.endsWith(".md")) : []);

test("add a record, take a note, find it by search, and see it in the vault", async ({ page }) => {
  // 1. Add a record (Discogs is mocked server-side with real saved responses).
  await page.goto("/add");
  await page.getByLabel("Discogs link").fill("https://www.discogs.com/release/9261843");
  await page.getByRole("button", { name: "Add record" }).click();
  await expect(page.getByTestId("job-analysis").getByRole("status")).toHaveText("done");
  await expect(page.getByTestId("job-discogs-sync").getByRole("status")).toHaveText("done");
  await expect(page.getByRole("heading", { name: "7_1 12-inch Mixes" })).toBeVisible();
  await expect(page.getByRole("row", { name: /Ambivalent Remix/ })).toContainText("120");

  // 2. Adding it again is reported, not duplicated.
  await page.getByRole("button", { name: "Add record" }).click();
  await expect(page.getByText("Already in your library.")).toBeVisible();

  // 3. Open it and write a prose note.
  await page.goto("/");
  await page.getByRole("link", { name: /7_1 12-inch Mixes/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "7_1 12-inch Mixes" })).toBeVisible();
  await page.getByPlaceholder("Huge energy").fill("Huge energy, the floor erupted at midnight.");
  await page.getByRole("button", { name: "Add note" }).click();
  await expect(page.getByText("Huge energy, the floor erupted at midnight.")).toBeVisible();

  // 4. A hand-entered BPM sticks, is marked manual, and survives a reload.
  await page.getByRole("button", { name: "Edit BPM for 7_1 (Ambivalent Remix)" }).click();
  await page.getByLabel("BPM for 7_1 (Ambivalent Remix)").fill("126.5");
  await page.getByLabel("BPM for 7_1 (Ambivalent Remix)").press("Enter");
  await expect(page.getByRole("row", { name: /Ambivalent Remix/ })).toContainText("manual");
  await page.reload();
  await expect(page.getByRole("row", { name: /Ambivalent Remix/ })).toContainText("126.5");

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
  expect(text).toContain("126.5 (manual)");
  expect(text).toContain("generated_by: vinyl-second-brain");
});

test("library filters live in the URL and the back button restores them", async ({ page, request }) => {
  await request.post("/api/records/intake", { data: { discogs_url: "https://www.discogs.com/release/46673", status: "owned" } });
  await page.goto("/");
  await expect(page.getByTestId("count")).toHaveText("2 records");

  await page.getByRole("button", { name: "9B, G major" }).click();
  await expect(page).toHaveURL(/key=9B/);
  await expect(page.getByTestId("count")).toHaveText("1 records");

  await page.getByRole("button", { name: "Table" }).click();
  await expect(page).toHaveURL(/view=table/);
  await page.goBack();
  await expect(page).not.toHaveURL(/view=table/);
  await page.goBack();
  await expect(page).not.toHaveURL(/key=/);
  await expect(page.getByTestId("count")).toHaveText("2 records");

  await page.goto("/?key=9B&view=tracks");
  await expect(page.getByTestId("count")).toHaveText("1 tracks");
  await expect(page.getByRole("button", { name: "9B, G major" })).toHaveAttribute("aria-pressed", "true");
});

test("settings: sync the vault and see the result", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByTestId("vault-dir")).toContainText("e2e/.run/vault");
  await page.getByRole("button", { name: "Sync vault now" }).click();
  await expect(page.getByTestId("last-result")).toContainText("unchanged");
});
