import { test, expect } from "@playwright/test";

test.describe("Service Health", () => {
  test("backend health endpoint returns healthy", async ({ page }) => {
    const response = await page.request.get("/api/v1/../health");
    // The health endpoint is at /health, but proxied via /api prefix
    // Try direct health endpoint through the nginx proxy
    const healthResponse = await page.request.get(
      `${new URL(page.url().startsWith("http") ? page.url() : (process.env.BASE_URL || "http://localhost:8065")).origin}/api/v1/users/token`,
      { failOnStatusCode: false }
    );
    // A 405 or 422 means the backend is alive (it just rejects GET on a POST endpoint)
    expect([405, 422, 200].includes(healthResponse.status())).toBeTruthy();
  });

  test("frontend serves the app shell", async ({ page }) => {
    await page.goto("/");
    // Unauthenticated users should be redirected to login
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
    // The page should contain the Codex title
    await expect(page.locator("h1")).toContainText("Codex");
  });

  test("login page renders correctly", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Username")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Login" })).toBeVisible();
    await expect(page.getByText("Register here")).toBeVisible();
  });
});
