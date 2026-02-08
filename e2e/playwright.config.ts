import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for Codex E2E tests.
 *
 * When run inside Docker Compose (CI=true), BASE_URL points to the frontend
 * container. For local development, it defaults to http://localhost:8065
 * (the default docker-compose.yml frontend port).
 */
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false, // tests share state (user registration etc.)
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1, // serial execution — tests build on each other
  reporter: process.env.CI ? "list" : "html",
  timeout: 30_000,

  use: {
    baseURL: process.env.BASE_URL || "http://localhost:8065",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  outputDir: "./test-results",

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
