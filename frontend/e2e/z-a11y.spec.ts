import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// Runs last (file name) against the same throwaway server; seeds what it needs, so it also works alone.
const pages = ["/", "/wantlist", "/add", "/search?mode=exact&q=floor", "/settings", "/record", "/?view=table", "/?view=tracks"];

for (const scheme of ["dark", "light"] as const) {
  test.describe(`accessibility (${scheme})`, () => {
    test.use({ colorScheme: scheme });

    let recordId = 0;
    test.beforeAll(async ({ request }) => {
      const res = await request.post("/api/records/intake", { data: { discogs_url: "https://www.discogs.com/release/9261843" } });
      recordId = (await res.json()).id;
    });

    for (const url of pages) {
      test(`no serious violations on ${url}`, async ({ page }) => {
        await page.goto(url === "/record" ? `/records/${recordId}` : url);
        await page.waitForLoadState("networkidle");
        if (url === "/record") await page.getByRole("button", { name: /Ambivalent/ }).first().click();
        const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
        const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
        expect(serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(" | ")}`)).toEqual([]);
      });
    }
  });
}
