import { defineConfig, devices } from "@playwright/test";
import { STORAGE_STATE } from "./global-setup";

/**
 * Playwright configuration for Codex E2E tests.
 *
 * Uses a global setup to register a shared user once, then runs test
 * suites in parallel with the saved auth state.
 */
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined, // auto-detect locally, cap at 2 in CI
  reporter: process.env.CI ? "list" : "html",
  timeout: 30_000,

  globalSetup: require.resolve("./global-setup"),

  use: {
    baseURL: process.env.BASE_URL || "http://localhost:8065",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
  },

  outputDir: "./test-results",

  projects: [
    // Auth tests don't use shared storageState — they test login/register flows
    {
      name: "auth",
      testMatch: /0[12]-.*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
      },
    },
    // All other tests run in parallel with shared auth
    {
      name: "chromium",
      testMatch: /0[3-9]-.*\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: STORAGE_STATE,
      },
    },
  ],
});
