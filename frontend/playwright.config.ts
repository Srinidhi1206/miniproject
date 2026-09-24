import { defineConfig, devices } from "@playwright/test";

// Expects the backend (:8000) and frontend (:3000) to be running.
// Uses an installed browser channel when PLAYWRIGHT_CHANNEL is set
// (e.g. "msedge" or "chrome"); otherwise Playwright's bundled Chromium.
const channel = process.env.PLAYWRIGHT_CHANNEL;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    ...(channel ? { channel } : {}),
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], ...(channel ? { channel } : {}) } },
    { name: "mobile", use: { ...devices["Pixel 7"], ...(channel ? { channel } : {}) } },
  ],
});
