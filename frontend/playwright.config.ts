import { defineConfig, devices } from "@playwright/test";

// E2E runs against the real stack: FastAPI on :8000, Next.js on :3000.
// Locally, already-running dev servers are reused; in CI both are started
// fresh with an isolated SQLite database and the bundled synthetic fixtures.
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    // WebKit = the Safari/iOS rendering engine; closest cross-engine proxy
    // for Safari on macOS and iOS available in CI.
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
  webServer: [
    {
      command:
        "cd ../backend && " +
        (process.env.CI ? "python" : ".venv/bin/python") +
        " -m uvicorn app.main:app --port 8000",
      url: "http://localhost:8000/api/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { DATABASE_URL: "sqlite:///./e2e.db" },
    },
    {
      command: "npm run start",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
  ],
});
