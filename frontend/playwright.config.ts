import { defineConfig } from "@playwright/test";

const port = 8100;

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  use: { baseURL: `http://127.0.0.1:${port}`, trace: "retain-on-failure", viewport: { width: 1280, height: 860 } },
  // The real app (built frontend + FastAPI) on one port, with a throwaway DB/vault and Discogs mocked.
  webServer: {
    command: "../.venv/bin/python ../backend/tests/e2e_server.py",
    url: `http://127.0.0.1:${port}/health`,
    reuseExistingServer: false,
    timeout: 30_000,
    env: { PORT: String(port), E2E_DIR: "e2e/.run", LOG_LEVEL: "WARNING", PYTHONPATH: "..:../backend" },
  },
});
